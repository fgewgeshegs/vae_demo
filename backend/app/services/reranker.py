"""Local BGE reranker service."""

from __future__ import annotations

import asyncio
from functools import lru_cache

from FlagEmbedding import FlagReranker

from app.core.config import settings
from app.services.bge_runtime import inference_slot
from app.services import inference_client

_last_error: str | None = None
_ready = False


@lru_cache(maxsize=1)
def _model() -> FlagReranker:
    return FlagReranker(
        settings.BGE_RERANKER_PATH,
        use_fp16=settings.BGE_DEVICE.startswith("cuda"),
    )


class Reranker:
    async def rerank(
        self,
        query: str,
        candidates: list[dict],
        limit: int | None = None,
    ) -> list[dict]:
        if not candidates:
            return []
        top_k = limit or settings.BGE_RERANK_TOP_K

        global _last_error, _ready
        if inference_client.enabled():
            try:
                scores = await inference_client.rerank(
                    query,
                    [item["content"] for item in candidates],
                )
                _ready = True
                _last_error = None
            except Exception as exc:
                _ready = False
                _last_error = f"remote inference: {exc}"
                raise
            return self._merge(candidates, scores, top_k)

        def score() -> list[float]:
            values = _model().compute_score(
                [[query, item["content"]] for item in candidates],
                normalize=True,
            )
            if isinstance(values, float):
                return [values]
            return [float(value) for value in values]

        async with inference_slot():
            try:
                scores = await asyncio.to_thread(score)
                _ready = True
                _last_error = None
            except Exception as exc:
                _ready = False
                _last_error = str(exc)
                raise
        return self._merge(candidates, scores, top_k)

    @staticmethod
    def _merge(candidates: list[dict], scores: list[float], top_k: int) -> list[dict]:
        if len(scores) != len(candidates):
            raise ValueError("Reranker returned an unexpected number of scores")
        reranked = []
        for item, rerank_score in zip(candidates, scores):
            result = dict(item)
            result["vector_score"] = result.get("score", 0.0)
            result["score"] = rerank_score
            result["rerank_score"] = rerank_score
            result["method"] = "bge_m3_pgvector_bge_reranker"
            reranked.append(result)
        return sorted(reranked, key=lambda item: item["score"], reverse=True)[:top_k]

    @staticmethod
    def status() -> dict:
        return {"ready": _ready, "last_error": _last_error}
