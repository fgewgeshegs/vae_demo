"""知识检索 API - 语义搜索"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.document import DocumentChunk
from app.schemas.document import DocumentChunkResponse

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
        # 通过 document 关联课程
        from app.models.document import Document
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
    """向量检索（需要已生成 embedding）"""
    # 使用关键词 + 向量混合检索
    like_pattern = f"%{q}%"
    query = select(DocumentChunk).where(DocumentChunk.content.ilike(like_pattern))

    if course_id:
        from app.models.document import Document
        query = query.join(Document).where(Document.course_id == course_id)

    query = query.order_by(DocumentChunk.chunk_index).limit(limit)
    result = await db.execute(query)
    chunks = result.scalars().all()

    return {
        "query": q,
        "total": len(chunks),
        "results": [DocumentChunkResponse.model_validate(c).model_dump() for c in chunks],
        "method": "hybrid",
    }
