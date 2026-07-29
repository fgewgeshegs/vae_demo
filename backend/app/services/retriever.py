"""RAG retriever backed primarily by Docker pgvector."""

from __future__ import annotations

from typing import List, Optional

from loguru import logger

from app.services.embedder import Embedder
from app.services.reranker import Reranker
from app.services.vector_store import VectorStore
from app.core.config import settings
from app.services.retrieval_errors import RetrievalBusyError, RetrievalUnavailableError
from app.services.retrieval_policy import filter_relevant
from app.services.redis_client import cache_get, cache_set
import hashlib


class Retriever:
    def __init__(self):
        self.embedder = Embedder()
        self.reranker = Reranker()
        self.vector_store = VectorStore()

    async def retrieve(
        self,
        query: str,
        course_id: Optional[int] = None,
        limit: int = 10,
        use_vector: bool = True,
        user_id: Optional[int] = None,
    ) -> List[dict]:
        cache_key = "retrieval:" + hashlib.sha256(
            f"{user_id}:{course_id}:{limit}:{query}".encode("utf-8")
        ).hexdigest()
        try:
            cached = await cache_get(cache_key)
            if cached is not None:
                return cached
        except Exception as exc:
            logger.warning(f"Retrieval cache read failed: {exc}")

        if use_vector:
            try:
                embedding = await self.embedder.embed(query)
                rows = await self.vector_store.search(
                    embedding,
                    settings.BGE_RETRIEVAL_CANDIDATES,
                    course_id,
                    user_id,
                )
                if rows:
                    candidates = [
                        {
                            "chunk_id": chunk.id,
                            "document_id": chunk.document_id,
                            "content": chunk.content,
                            "score": score,
                            "method": "bge_m3_pgvector",
                            **(chunk.chunk_metadata or {}),
                        }
                        for chunk, score in rows
                    ]
                    reranked = await self.reranker.rerank(query, candidates, limit)
                    results = filter_relevant(reranked)
                    try:
                        await cache_set(
                            cache_key, results, settings.RETRIEVAL_CACHE_TTL_SECONDS
                        )
                    except Exception as exc:
                        logger.warning(f"Retrieval cache write failed: {exc}")
                    return results
            except RetrievalBusyError:
                raise
            except Exception as exc:
                logger.exception(f"Docker pgvector retrieval failed: {exc}")
                raise RetrievalUnavailableError(
                    f"Knowledge retrieval service is unavailable: {type(exc).__name__}"
                ) from exc

        return []
