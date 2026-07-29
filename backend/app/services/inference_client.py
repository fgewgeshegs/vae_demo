"""Shared HTTP client for the optional standalone BGE inference service."""

from __future__ import annotations

import httpx

from app.core.config import settings

_client: httpx.AsyncClient | None = None


def enabled() -> bool:
    return bool(settings.BGE_INFERENCE_SERVICE_URL)


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=str(settings.BGE_INFERENCE_SERVICE_URL).rstrip("/"),
            timeout=settings.BGE_INFERENCE_TIMEOUT_SECONDS,
        )
    return _client


async def embed(texts: list[str]) -> list[list[float]]:
    response = await _get_client().post("/embed", json={"texts": texts})
    response.raise_for_status()
    return response.json()["embeddings"]


async def rerank(query: str, documents: list[str]) -> list[float]:
    response = await _get_client().post(
        "/rerank",
        json={"query": query, "documents": documents},
    )
    response.raise_for_status()
    return response.json()["scores"]


async def close_inference_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
