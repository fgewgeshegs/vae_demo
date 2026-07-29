"""Verify local BGE models and the end-to-end retrieval chain."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.embedder import Embedder
from app.services.reranker import Reranker
from app.services.retriever import Retriever


async def main() -> None:
    vector = await Embedder().embed("什么是人工智能？")
    print(f"[OK] BGE-M3 dimension={len(vector)}")

    reranked = await Reranker().rerank(
        "什么是人工智能？",
        [
            {"content": "人工智能研究如何让机器表现出智能行为。", "score": 0.8},
            {"content": "今天的天气很好。", "score": 0.7},
        ],
        limit=2,
    )
    print(f"[OK] reranker top_score={reranked[0]['score']:.4f}")

    results = await Retriever().retrieve("什么是人工智能？", limit=5)
    print(f"[OK] pgvector results={len(results)}")
    for index, item in enumerate(results, 1):
        print(
            f"{index}. score={item['score']:.4f} "
            f"source={item.get('source', '')} locator={item.get('locator', '')}"
        )


if __name__ == "__main__":
    asyncio.run(main())
