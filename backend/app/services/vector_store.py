"""向量存储服务 - pgvector"""

from __future__ import annotations

from typing import List, Tuple, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.document import DocumentChunk


class VectorStore:
    """pgvector 向量存储"""

    async def search(
        self,
        embedding: List[float],
        limit: int = 10,
        course_id: Optional[int] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        """向量相似度搜索（使用余弦距离）"""
        async with async_session_factory() as db:
            if course_id:
                query = text(
                    """
                    SELECT dc.id, dc.document_id, dc.chunk_index, dc.content, dc.metadata,
                           1 - (dc.embedding <=> :embedding::vector(1536)) AS similarity
                    FROM document_chunks dc
                    JOIN documents d ON d.id = dc.document_id
                    WHERE dc.embedding IS NOT NULL AND d.course_id = :course_id
                    ORDER BY similarity DESC
                    LIMIT :limit
                    """
                )
                params = {
                    "embedding": str(embedding),
                    "course_id": course_id,
                    "limit": limit,
                }
            else:
                query = text(
                    """
                    SELECT dc.id, dc.document_id, dc.chunk_index, dc.content, dc.metadata,
                           1 - (dc.embedding <=> :embedding::vector(1536)) AS similarity
                    FROM document_chunks dc
                    JOIN documents d ON d.id = dc.document_id
                    WHERE dc.embedding IS NOT NULL
                    ORDER BY similarity DESC
                    LIMIT :limit
                    """
                )
                params = {
                    "embedding": str(embedding),
                    "limit": limit,
                }

            result = await db.execute(query, params)
            rows = result.fetchmany(limit)

            chunks = []
            for row in rows:
                chunk = DocumentChunk(
                    id=row.id,
                    document_id=row.document_id,
                    chunk_index=row.chunk_index,
                    content=row.content,
                    metadata=row.metadata,
                )
                chunks.append((chunk, float(row.similarity)))

            return chunks
