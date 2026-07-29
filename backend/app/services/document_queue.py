from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from loguru import logger

from app.core.config import settings
from app.services.redis_client import get_redis

QUEUE_NAME = "document-processing"
PROCESSING_NAME = "document-processing:active"
DEAD_LETTER_NAME = "document-processing:failed"
STATUS_PREFIX = "document-task:"


def _payload(doc_id: int, attempts: int = 0) -> str:
    return json.dumps({"doc_id": doc_id, "attempts": attempts})


def _parse_payload(item: str) -> dict:
    try:
        parsed = json.loads(item)
        if isinstance(parsed, dict):
            return parsed
        return {"doc_id": int(parsed), "attempts": 0}
    except json.JSONDecodeError:
        return {"doc_id": int(item), "attempts": 0}


async def _set_status(doc_id: int, status: str, **details) -> None:
    data = {
        "doc_id": str(doc_id),
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **{key: str(value) for key, value in details.items()},
    }
    key = f"{STATUS_PREFIX}{doc_id}"
    await get_redis().hset(key, mapping=data)
    await get_redis().expire(key, 7 * 24 * 60 * 60)


async def enqueue_document(doc_id: int) -> None:
    await get_redis().rpush(QUEUE_NAME, _payload(doc_id))
    await _set_status(doc_id, "queued", attempts=0)


async def get_document_task_status(doc_id: int) -> dict:
    return await get_redis().hgetall(f"{STATUS_PREFIX}{doc_id}")


async def run_document_worker() -> None:
    from app.api.v1.documents import process_document

    logger.info("Document queue worker started")
    while item := await get_redis().rpop(PROCESSING_NAME):
        await get_redis().lpush(QUEUE_NAME, item)

    while True:
        try:
            item = await get_redis().brpoplpush(QUEUE_NAME, PROCESSING_NAME, timeout=5)
            if not item:
                continue
            task = _parse_payload(item)
            doc_id = int(task["doc_id"])
            attempts = int(task.get("attempts", 0)) + 1
            await _set_status(doc_id, "processing", attempts=attempts)
            try:
                await process_document(doc_id)
            except Exception as exc:
                await get_redis().lrem(PROCESSING_NAME, 1, item)
                if attempts < settings.DOCUMENT_TASK_MAX_RETRIES:
                    await get_redis().lpush(QUEUE_NAME, _payload(doc_id, attempts))
                    await _set_status(doc_id, "retrying", attempts=attempts, error=exc)
                else:
                    await get_redis().lpush(DEAD_LETTER_NAME, _payload(doc_id, attempts))
                    await _set_status(doc_id, "failed", attempts=attempts, error=exc)
                logger.exception(f"Document task #{doc_id} failed on attempt {attempts}")
                continue
            await get_redis().lrem(PROCESSING_NAME, 1, item)
            await _set_status(doc_id, "completed", attempts=attempts)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Document queue worker failed; retrying")
            await asyncio.sleep(2)
