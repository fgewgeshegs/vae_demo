"""RAG 检索器 - 混合检索"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.document import DocumentChunk
from app.services.embedder import Embedder
from app.services.vector_store import VectorStore


class Retriever:
    """RAG 检索器 - 混合检索（关键词 + 向量）"""

    def __init__(self):
        self.embedder = Embedder()
        self.vector_store = VectorStore()

    async def retrieve(
        self,
        query: str,
        course_id: Optional[int] = None,
        limit: int = 10,
        use_vector: bool = False,
    ) -> List[dict]:
        """混合检索"""
        results = []

        # 1. 关键词检索
        async with async_session_factory() as db:
            like_pattern = f"%{query}%"
            sql_query = select(DocumentChunk).where(DocumentChunk.content.ilike(like_pattern))
            if course_id:
                from app.models.document import Document
                sql_query = sql_query.join(Document).where(Document.course_id == course_id)
            sql_query = sql_query.limit(limit)
            result = await db.execute(sql_query)
            for chunk in result.scalars().all():
                results.append({
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "content": chunk.content[:500],
                    "score": 1.0,
                    "method": "keyword",
                })

        # 2. 向量检索（如果启用）
        if use_vector:
            try:
                embedding = await self.embedder.embed(query)
                vec_results = await self.vector_store.search(embedding, limit, course_id)
                for chunk, score in vec_results:
                    # 去重
                    if not any(r["chunk_id"] == chunk.id for r in results):
                        results.append({
                            "chunk_id": chunk.id,
                            "document_id": chunk.document_id,
                            "content": chunk.content[:500],
                            "score": score,
                            "method": "vector",
                        })
            except Exception:
                pass

        return results[:limit]
