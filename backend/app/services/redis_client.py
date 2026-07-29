from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def cache_get(key: str) -> Any | None:
    value = await get_redis().get(key)
    return json.loads(value) if value is not None else None


async def cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    await get_redis().set(key, json.dumps(value, ensure_ascii=False), ex=ttl_seconds)


async def delete_pattern(pattern: str) -> int:
    deleted = 0
    async for key in get_redis().scan_iter(match=pattern, count=100):
        deleted += await get_redis().delete(key)
    return deleted


async def invalidate_cache(pattern: str) -> None:
    try:
        await delete_pattern(pattern)
    except Exception:
        # Cache invalidation must not make the primary database operation fail.
        return


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
