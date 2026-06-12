"""知识检索 API - 语义搜索"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.document import DocumentChunk, Document
from app.schemas.document import DocumentChunkResponse
from app.services.vector_store import VectorStore
from app.services.embedder import Embedder

router = APIRouter()


@router.get("/", response_model=dict)
async def semantic_search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    course_id: int | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """语义搜索（基于向量 + 关键词混合）"""
    # 先尝试关键词搜索（当 pgvector 向量还未就绪时）
    like_pattern = f"%{q}%"
    query = select(DocumentChunk).where(DocumentChunk.content.ilike(like_pattern))

    if course_id:
        query = query.join(Document).where(Document.course_id == course_id)

    query = query.order_by(DocumentChunk.chunk_index).limit(limit)
    result = await db.execute(query)
    chunks = result.scalars().all()

    return {
        "query": q,
        "total": len(chunks),
        "results": [DocumentChunkResponse.model_validate(c).model_dump() for c in chunks],
        "method": "keyword",
    }


@router.get("/vector", response_model=dict)
async def vector_search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    course_id: int | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """向量检索（基于 pgvector 余弦相似度 + 关键词混合）"""
    vector_store = VectorStore()
    embedder = Embedder()

    # 1. 生成查询向量
    embedding = await embedder.embed(q)

    # 2. 检查是否有真实向量（非零向量）
    has_real_vector = any(abs(v) > 0.001 for v in embedding)

    if has_real_vector:
        # 向量检索
        vec_results = await vector_store.search(
            embedding=embedding,
            limit=limit,
            course_id=course_id,
        )

        vector_items = []
        for chunk, score in vec_results:
            vector_items.append({
                "id": chunk.id,
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "metadata": chunk.metadata,
                "relevance_score": round(score, 4),
            })

        # 补充关键词结果（去重）
        like_pattern = f"%{q}%"
        kw_query = select(DocumentChunk).where(DocumentChunk.content.ilike(like_pattern))
        if course_id:
            kw_query = kw_query.join(Document).where(Document.course_id == course_id)
        kw_query = kw_query.order_by(DocumentChunk.chunk_index).limit(limit)

        result = await db.execute(kw_query)
        kw_chunks = result.scalars().all()

        existing_ids = {item["id"] for item in vector_items}
        kw_items = []
        for c in kw_chunks:
            if c.id not in existing_ids:
                kw_items.append({
                    "id": c.id,
                    "document_id": c.document_id,
                    "chunk_index": c.chunk_index,
                    "content": c.content,
                    "metadata": c.metadata,
                    "relevance_score": 0.5,
                })

        all_results = vector_items + kw_items

        return {
            "query": q,
            "total": len(all_results),
            "results": all_results[:limit],
            "method": "hybrid",
            "vector_search": True,
        }
    else:
        # 无真实向量时，回退到关键词搜索
        like_pattern = f"%{q}%"
        query = select(DocumentChunk).where(DocumentChunk.content.ilike(like_pattern))
        if course_id:
            query = query.join(Document).where(Document.course_id == course_id)
        query = query.order_by(DocumentChunk.chunk_index).limit(limit)
        result = await db.execute(query)
        chunks = result.scalars().all()

        return {
            "query": q,
            "total": len(chunks),
            "results": [DocumentChunkResponse.model_validate(c).model_dump() for c in chunks],
            "method": "keyword_fallback",
            "vector_search": False,
        }
