"""Benchmark exact scan, HNSW, and reciprocal-rank-fusion hybrid retrieval."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

from sqlalchemy import text

from app.core.database import async_session_factory, close_db
from app.services.embedder import Embedder

DEFAULT_QUERIES = [
    "什么是机器学习",
    "如何制定学习计划",
    "深度学习的基本原理",
    "怎样评估学习效果",
]


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(int(len(ordered) * fraction), len(ordered) - 1)]


async def vector_search(embedding: list[float], limit: int, exact: bool) -> tuple[list[int], float]:
    started = time.perf_counter()
    async with async_session_factory() as db:
        if exact:
            await db.execute(text("SET LOCAL enable_indexscan = off"))
            await db.execute(text("SET LOCAL enable_bitmapscan = off"))
        else:
            await db.execute(text("SET LOCAL enable_seqscan = off"))
        rows = (
            await db.execute(
                text(
                    """
                    SELECT id
                    FROM document_chunks
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:embedding AS vector)
                    LIMIT :limit
                    """
                ),
                {"embedding": str(embedding), "limit": limit},
            )
        ).fetchall()
    return [row.id for row in rows], (time.perf_counter() - started) * 1000


async def keyword_search(query: str, limit: int) -> tuple[list[int], float]:
    started = time.perf_counter()
    async with async_session_factory() as db:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT id
                    FROM document_chunks
                    WHERE content ILIKE :query
                    ORDER BY id
                    LIMIT :limit
                    """
                ),
                {"query": f"%{query}%", "limit": limit},
            )
        ).fetchall()
    return [row.id for row in rows], (time.perf_counter() - started) * 1000


def rrf(*rankings: list[int], limit: int) -> list[int]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0) + 1 / (60 + rank)
    return [item_id for item_id, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]]


async def index_definitions() -> list[str]:
    async with async_session_factory() as db:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT indexdef FROM pg_indexes
                    WHERE tablename = 'document_chunks' AND indexdef ILIKE '%embedding%'
                    ORDER BY indexname
                    """
                )
            )
        ).fetchall()
    return [row.indexdef for row in rows]


async def run(queries: list[str], limit: int) -> dict:
    indexes = await index_definitions()
    embeddings = await Embedder().embed_batch(queries)
    exact_latencies, hnsw_latencies, hybrid_latencies, recalls, hybrid_unique = [], [], [], [], []
    for query, embedding in zip(queries, embeddings):
        exact_ids, exact_ms = await vector_search(embedding, limit, exact=True)
        hnsw_ids, hnsw_ms = await vector_search(embedding, limit, exact=False)
        keyword_ids, keyword_ms = await keyword_search(query, limit)
        hybrid_ids = rrf(hnsw_ids, keyword_ids, limit=limit)
        exact_latencies.append(exact_ms)
        hnsw_latencies.append(hnsw_ms)
        hybrid_latencies.append(hnsw_ms + keyword_ms)
        recalls.append(len(set(exact_ids) & set(hnsw_ids)) / max(len(exact_ids), 1))
        hybrid_unique.append(len(set(hybrid_ids) - set(hnsw_ids)))

    def latency(values: list[float]) -> dict:
        return {
            "mean_ms": round(statistics.mean(values), 2),
            "p50_ms": round(percentile(values, 0.50), 2),
            "p95_ms": round(percentile(values, 0.95), 2),
        }

    return {
        "queries": len(queries),
        "top_k": limit,
        "indexes": indexes,
        "hnsw_present": any("USING hnsw" in definition for definition in indexes),
        "exact": latency(exact_latencies),
        "indexed_vector": {
            **latency(hnsw_latencies),
            "mean_recall_at_k": round(statistics.mean(recalls), 4),
            "note": "If multiple vector indexes exist, PostgreSQL chooses the index.",
        },
        "hybrid_rrf": {
            **latency(hybrid_latencies),
            "mean_keyword_only_results_at_k": round(statistics.mean(hybrid_unique), 2),
            "note": "Coverage metric only; relevance quality requires labeled judgments.",
        },
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries-file", type=Path)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()
    queries = DEFAULT_QUERIES
    if args.queries_file:
        queries = [line.strip() for line in args.queries_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    try:
        print(json.dumps(await run(queries, args.top_k), ensure_ascii=False, indent=2))
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
