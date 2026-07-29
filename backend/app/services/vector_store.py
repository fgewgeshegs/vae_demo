"""pgvector storage and similarity search."""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import text

from app.core.database import async_session_factory
from app.models.document import DocumentChunk


class VectorStore:
    async def search(
        self,
        embedding: List[float],
        limit: int = 10,
        course_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        async with async_session_factory() as db:
            course_filter = "AND d.course_id = :course_id" if course_id else ""
            user_filter = "AND (d.user_id = :user_id OR d.user_id IS NULL)" if user_id else ""
            query = text(
                f"""
                SELECT dc.id, dc.document_id, dc.chunk_index, dc.content,
                       dc.metadata AS chunk_metadata,
                       1 - (dc.embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM document_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE dc.embedding IS NOT NULL {course_filter} {user_filter}
                ORDER BY dc.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
                """
            )
            params = {"embedding": str(embedding), "limit": limit}
            if course_id:
                params["course_id"] = course_id
            if user_id:
                params["user_id"] = user_id

            rows = (await db.execute(query, params)).fetchall()
            return [
                (
                    DocumentChunk(
                        id=row.id,
                        document_id=row.document_id,
                        chunk_index=row.chunk_index,
                        content=row.content,
                        chunk_metadata=row.chunk_metadata,
                    ),
                    float(row.similarity),
                )
                for row in rows
            ]
