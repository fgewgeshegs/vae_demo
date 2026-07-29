"""Local offline knowledge-base retrieval backed by hashing vectors and FAISS."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from loguru import logger
from app.services.offline_hashing import hashing_embedding

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_KB_DIR = PROJECT_ROOT.parent / "knowledge-base"
SEGMENT_RE = re.compile(r"[\u4e00-\u9fff]+|[A-Za-z0-9_]+")
QUESTION_PREFIXES = ("什么是", "什么叫", "请解释", "解释", "简述", "说明")


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for segment in SEGMENT_RE.findall(text.lower()):
        if re.fullmatch(r"[\u4e00-\u9fff]+", segment):
            tokens.extend(segment)
            for size in (2, 3, 4):
                tokens.extend(segment[index : index + size] for index in range(len(segment) - size + 1))
        else:
            tokens.append(segment)
    return tokens


class HashingEncoder:
    def __init__(self, dimensions: int = 1024):
        self.dimensions = dimensions

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(
            [hashing_embedding(text, self.dimensions) for text in texts],
            dtype="float32",
        )


class BM25:
    def __init__(self, texts: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(text)) for text in texts]
        self.lengths = [sum(doc.values()) for doc in self.docs]
        self.avg_length = sum(self.lengths) / max(len(self.lengths), 1)
        frequencies = Counter(token for doc in self.docs for token in doc)
        count = len(self.docs)
        self.idf = {
            token: math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
            for token, frequency in frequencies.items()
        }
        self.postings: dict[str, list[tuple[int, int]]] = {}
        for index, doc in enumerate(self.docs):
            for token, frequency in doc.items():
                self.postings.setdefault(token, []).append((index, frequency))

    def search(self, query: str, limit: int) -> list[tuple[int, float]]:
        scores: Counter[int] = Counter()
        for token in set(tokenize(query)):
            for index, frequency in self.postings.get(token, []):
                norm = frequency + self.k1 * (
                    1 - self.b + self.b * self.lengths[index] / max(self.avg_length, 1)
                )
                scores[index] += self.idf.get(token, 0.0) * frequency * (self.k1 + 1) / norm
        return scores.most_common(limit)


class LocalKnowledgeBase:
    def __init__(self, kb_dir: Path = DEFAULT_KB_DIR):
        self.kb_dir = kb_dir
        metadata_path = kb_dir / "embeddings" / "metadata.json"
        index_path = kb_dir / "db" / "faiss.index"
        if not metadata_path.exists() or not index_path.exists():
            raise FileNotFoundError(f"Local knowledge base is incomplete: {kb_dir}")
        self.chunks: list[dict[str, Any]] = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.index = faiss.read_index(str(index_path))
        self.encoder = HashingEncoder(self.index.d)
        self.bm25 = BM25([chunk["text"] for chunk in self.chunks])
        logger.info(f"Local knowledge base loaded: chunks={len(self.chunks)}, dir={kb_dir}")

    @staticmethod
    def _focus(query: str) -> str:
        focus = query.strip().rstrip("？?")
        for prefix in QUESTION_PREFIXES:
            if focus.startswith(prefix):
                focus = focus[len(prefix) :]
                break
        return focus.strip("：:，,。 ") or query

    def _intent_bonus(self, query: str, text: str) -> float:
        focus = self._focus(query)
        bonus = min(text.count(focus), 3) * 0.012 if len(focus) >= 2 else 0.0
        if query.startswith(QUESTION_PREFIXES) and any(word in text for word in ("定义", "是指", "称为")):
            bonus += 0.018
        return bonus

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        candidate_count = min(max(limit * 6, 30), len(self.chunks))
        vector = self.encoder.encode([f"为这个句子生成表示以用于检索相关文章：{query}"])
        vector_scores, vector_indices = self.index.search(vector.astype("float32"), candidate_count)
        vector_ranking = [
            (int(index), float(score))
            for index, score in zip(vector_indices[0], vector_scores[0])
            if index >= 0
        ]
        bm25_ranking = self.bm25.search(query, candidate_count)
        fused: Counter[int] = Counter()
        for ranking, weight in ((vector_ranking, 0.25), (bm25_ranking, 1.5)):
            for rank, (index, _) in enumerate(ranking, 1):
                fused[index] += weight / (60 + rank)
        for index in list(fused):
            fused[index] += self._intent_bonus(query, self.chunks[index]["text"])

        results = []
        for index, score in sorted(fused.items(), key=lambda item: item[1], reverse=True)[:limit]:
            chunk = self.chunks[index]
            results.append(
                {
                    "chunk_id": chunk.get("id", f"local-{index}"),
                    "document_id": None,
                    "content": chunk["text"],
                    "score": float(score),
                    "method": "local_hybrid",
                    "source": chunk.get("source", ""),
                    "locator": chunk.get("locator", ""),
                    "title": chunk.get("title", ""),
                    "type": chunk.get("type", "textbook"),
                    "assets": chunk.get("assets", []),
                }
            )
        return results

    def status(self) -> dict[str, Any]:
        return {
            "available": True,
            "chunks": len(self.chunks),
            "dimension": self.index.d,
            "index_size": self.index.ntotal,
            "path": str(self.kb_dir),
        }


@lru_cache(maxsize=1)
def get_local_knowledge_base() -> LocalKnowledgeBase:
    return LocalKnowledgeBase()
