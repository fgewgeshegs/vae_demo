"""学习行为记录服务 - 记录和分析用户学习行为"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.learning_behavior import LearningBehavior
from app.core.config import settings
from loguru import logger


class BehaviorService:
    """学习行为记录服务"""

    @staticmethod
    async def record(
        user_id: int,
        action_type: str,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        metadata: Optional[dict] = None,
        duration_seconds: int = 0,
    ) -> LearningBehavior | None:
        """记录一条学习行为"""
        try:
            async with async_session_factory() as db:
                behavior = LearningBehavior(
                    user_id=user_id,
                    action_type=action_type,
                    target_type=target_type,
                    target_id=target_id,
                    behavior_metadata=metadata or {},
                    duration_seconds=duration_seconds,
                )
                db.add(behavior)
                await db.commit()
                await db.refresh(behavior)
                return behavior
        except Exception as e:
            logger.error(f"记录学习行为失败: {e}")
            return None

    @staticmethod
    async def get_user_stats(user_id: int, course_id: Optional[int] = None) -> dict:
        """获取用户学习行为统计"""
        async with async_session_factory() as db:
            since = datetime.now(timezone.utc) - timedelta(days=settings.ANALYTICS_LOOKBACK_DAYS)
            base_filters = (
                LearningBehavior.user_id == user_id,
                LearningBehavior.created_at >= since,
            )
            summary = (
                await db.execute(
                    select(
                        func.count(LearningBehavior.id),
                        func.coalesce(func.sum(LearningBehavior.duration_seconds), 0),
                        func.count(func.distinct(func.date(LearningBehavior.created_at))),
                    ).where(*base_filters)
                )
            ).one()
            action_rows = (
                await db.execute(
                    select(LearningBehavior.action_type, func.count(LearningBehavior.id))
                    .where(*base_filters)
                    .group_by(LearningBehavior.action_type)
                )
            ).all()
            daily_rows = (
                await db.execute(
                    select(func.date(LearningBehavior.created_at), func.count(LearningBehavior.id))
                    .where(*base_filters)
                    .group_by(func.date(LearningBehavior.created_at))
                )
            ).all()
            total_count, total_duration, active_days = summary
            action_type_counts = dict(action_rows)
            daily_counts = {day.isoformat(): count for day, count in daily_rows}

            return {
                "total_count": total_count,
                "action_types": action_type_counts,
                "total_duration_minutes": round(total_duration / 60, 1),
                "active_days": active_days,
                "daily_counts": daily_counts,
            }

    @staticmethod
    async def get_recent_activities(
        user_id: int,
        limit: int = 20,
    ) -> list[dict]:
        """获取最近学习活动"""
        async with async_session_factory() as db:
            query = (
                select(LearningBehavior)
                .where(LearningBehavior.user_id == user_id)
                .order_by(LearningBehavior.created_at.desc())
                .limit(limit)
            )
            result = await db.execute(query)
            behaviors = result.scalars().all()

            return [
                {
                    "id": b.id,
                    "action_type": b.action_type,
                    "target_type": b.target_type,
                    "target_id": b.target_id,
                    "metadata": b.behavior_metadata,
                    "duration_seconds": b.duration_seconds,
                    "created_at": b.created_at.isoformat() if b.created_at else None,
                }
                for b in behaviors
            ]


# 行为类型常量
class ActionType:
    """学习行为类型"""
    # 浏览行为
    VIEW_COURSE = "view_course"
    VIEW_CHAPTER = "view_chapter"
    VIEW_RESOURCE = "view_resource"
    VIEW_DOCUMENT = "view_document"

    # 学习行为
    START_LEARNING = "start_learning"
    COMPLETE_LEARNING = "complete_learning"
    REVIEW_NODE = "review_node"

    # 练习行为
    START_EXERCISE = "start_exercise"
    COMPLETE_EXERCISE = "complete_exercise"
    EXERCISE_CORRECT = "exercise_correct"
    EXERCISE_WRONG = "exercise_wrong"

    # 问答行为
    ASK_QUESTION = "ask_question"
    VIEW_ANSWER = "view_answer"

    # 评估行为
    GENERATE_EVALUATION = "generate_evaluation"

    # 系统行为
    LOGIN = "login"
    LOGOUT = "logout"
    RUN_LEARNING_TASK = "run_learning_task"
