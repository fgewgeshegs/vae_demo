import asyncio
from contextlib import asynccontextmanager

from app.core.config import settings
from app.services.retrieval_errors import RetrievalBusyError


inference_gate = asyncio.Semaphore(settings.BGE_MAX_CONCURRENCY)
active_inferences = 0
waiting_inferences = 0


@asynccontextmanager
async def inference_slot():
    global active_inferences, waiting_inferences
    waiting_inferences += 1
    try:
        try:
            await asyncio.wait_for(
                inference_gate.acquire(),
                timeout=settings.BGE_QUEUE_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise RetrievalBusyError(
                "GPU inference is busy; retry after a few seconds"
            ) from exc
    finally:
        waiting_inferences -= 1

    active_inferences += 1
    try:
        yield
    finally:
        active_inferences -= 1
        inference_gate.release()


def runtime_status() -> dict:
    return {
        "max_concurrency": settings.BGE_MAX_CONCURRENCY,
        "active": active_inferences,
        "waiting": waiting_inferences,
        "queue_timeout_seconds": settings.BGE_QUEUE_TIMEOUT_SECONDS,
    }
