"""Deterministic offline text embeddings for development and deployment."""

from __future__ import annotations

import hashlib
import math
import re


def hashing_embedding(text: str, dimensions: int = 1024) -> list[float]:
    """Create a normalized signed-hashing vector without external models."""
    vector = [0.0] * dimensions
    units = re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", text.lower())
    features = units + [
        "".join(units[index : index + 2]) for index in range(len(units) - 1)
    ]

    for feature in features:
        value = int.from_bytes(
            hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest(),
            "little",
        )
        vector[value % dimensions] += 1.0 if value & 1 else -1.0

    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector
