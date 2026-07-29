"""Background processor for lightweight learning-domain events."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.learning_event import LearningEvent
from app.models.qa_record import QARecord
from app.services.event_service import EventType


class EventProcessor:
    """Process a small, explicit subset of events.

    The first feedback loop is intentionally narrow:
    qa_answered -> ProfileAgent analyzes whether the learner profile should change.
    """

    def __init__(self, batch_size: int = 5):
        self.batch_size = batch_size

    async def process_pending(self) -> int:
        events = await self._claim_pending_qa_events()
        processed = 0
        for event in events:
            await self._process_event(event)
            processed += 1
        return processed

    async def _claim_pending_qa_events(self) -> list[LearningEvent]:
        async with async_session_factory() as db:
            events = (
                await db.execute(
                    select(LearningEvent)
                    .where(
                        LearningEvent.status == "pending",
                        LearningEvent.event_type == EventType.QA_ANSWERED,
                    )
                    .order_by(LearningEvent.created_at)
                    .limit(self.batch_size)
                )
            ).scalars().all()
            for event in events:
                event.status = "processing"
            await db.commit()
            return events

    async def _process_event(self, event: LearningEvent) -> None:
        try:
            if event.event_type == EventType.QA_ANSWERED:
                await self._process_qa_answered(event)
            await self._mark_processed(event.id)
        except Exception as exc:
            logger.exception(f"Learning event #{event.id} failed")
            await self._mark_failed(event.id, str(exc))

    async def _process_qa_answered(self, event: LearningEvent) -> None:
        if event.target_type != "qa_record" or not event.target_id:
            raise ValueError("qa_answered event must target a qa_record")

        async with async_session_factory() as db:
            record = (
                await db.execute(
                    select(QARecord).where(
                        QARecord.id == event.target_id,
                        QARecord.user_id == event.user_id,
                    )
                )
            ).scalar_one_or_none()
            if not record:
                raise ValueError(f"QA record #{event.target_id} not found")

            question = record.question
            answer = record.answer or ""

        from app.agents.profile_agent import ProfileAgent

        message = (
            "Analyze this completed tutoring exchange and update the learner profile only "
            "when it reveals durable learning goals, knowledge gaps, weak points, interests, "
            "or cognitive preferences.\n\n"
            f"Question:\n{question}\n\n"
            f"Answer:\n{answer}"
        )
        result = await ProfileAgent().process(
            {
                "user_id": event.user_id,
                "course_id": event.course_id,
                "message": message,
                "source_event_id": event.id,
            }
        )
        if result.get("type") == "profile_error":
            raise RuntimeError(result.get("error") or "Profile update failed")

    async def _mark_processed(self, event_id: int) -> None:
        await self._mark(event_id, "processed")

    async def _mark_failed(self, event_id: int, error: str) -> None:
        await self._mark(event_id, "failed", error=error)

    async def _mark(self, event_id: int, status: str, error: str | None = None) -> None:
        async with async_session_factory() as db:
            event = (
                await db.execute(select(LearningEvent).where(LearningEvent.id == event_id))
            ).scalar_one_or_none()
            if not event:
                return
            event.status = status
            event.error = error
            event.processed_at = datetime.now(timezone.utc)
            await db.commit()


async def run_event_processor() -> None:
    processor = EventProcessor()
    logger.info("Learning event processor started")
    while True:
        try:
            count = await processor.process_pending()
            await asyncio.sleep(1 if count else 5)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Learning event processor failed; retrying")
            await asyncio.sleep(5)
