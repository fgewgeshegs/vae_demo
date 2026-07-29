"""Local BGE-M3 embedding service used by Docker pgvector."""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.services.bge_runtime import inference_slot
from app.services import inference_client

_last_error: str | None = None
_ready = False


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(
        settings.BGE_MODEL_PATH,
        device=settings.BGE_DEVICE,
        local_files_only=True,
        model_kwargs={"low_cpu_mem_usage": False},
    )


class Embedder:
    """Generate normalized dense vectors using the local BGE-M3 model."""

    def __init__(self):
        self.model_name = "BAAI/bge-m3"
        self.dimension = settings.BGE_EMBEDDING_DIMENSION

    async def embed(self, text: str) -> List[float]:
        vectors = await self.embed_batch([text])
        return vectors[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        global _last_error, _ready
        if inference_client.enabled():
            try:
                result = await inference_client.embed(texts)
                if any(len(vector) != self.dimension for vector in result):
                    raise ValueError("Unexpected remote BGE embedding dimension")
                _ready = True
                _last_error = None
                return result
            except Exception as exc:
                _ready = False
                _last_error = f"remote inference: {exc}"
                raise

        def encode() -> List[List[float]]:
            vectors = _model().encode(
                texts,
                batch_size=16,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            if vectors.shape[1] != self.dimension:
                raise ValueError(
                    f"Unexpected BGE embedding dimension: {vectors.shape[1]}"
                )
            return vectors.tolist()

        async with inference_slot():
            try:
                result = await asyncio.to_thread(encode)
                _ready = True
                _last_error = None
                return result
            except Exception as exc:
                _ready = False
                _last_error = str(exc)
                raise

    @staticmethod
    def status() -> dict:
        return {"ready": _ready, "last_error": _last_error}
