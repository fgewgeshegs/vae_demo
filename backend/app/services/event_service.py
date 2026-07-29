"""Lightweight domain-event persistence for agent coordination."""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.core.database import async_session_factory
from app.models.learning_event import LearningEvent


class EventType:
    QA_ANSWERED = "qa_answered"
    PROFILE_UPDATED = "profile_updated"
    PATH_GENERATED = "path_generated"
    RESOURCE_GENERATED = "resource_generated"
    NODE_COMPLETED = "node_completed"
    EVALUATION_GENERATED = "evaluation_generated"


class EventService:
    """Persist domain events; processing is intentionally deferred."""

    @staticmethod
    async def emit(
        *,
        user_id: int,
        event_type: str,
        course_id: int | None = None,
        source_agent: str | None = None,
        target_type: str | None = None,
        target_id: int | None = None,
        payload: dict[str, Any] | None = None,
        status: str = "pending",
    ) -> LearningEvent | None:
        try:
            async with async_session_factory() as db:
                event = LearningEvent(
                    user_id=user_id,
                    course_id=course_id,
                    event_type=event_type,
                    source_agent=source_agent,
                    target_type=target_type,
                    target_id=target_id,
                    payload=payload or {},
                    status=status,
                )
                db.add(event)
                await db.commit()
                await db.refresh(event)
                return event
        except Exception as exc:
            logger.error(f"Failed to emit learning event {event_type}: {exc}")
            return None
