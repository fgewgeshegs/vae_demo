"""学习行为记录服务 - 记录和分析用户学习行为"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.learning_behavior import LearningBehavior
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
            query = select(LearningBehavior).where(
                LearningBehavior.user_id == user_id
            )

            result = await db.execute(query)
            behaviors = result.scalars().all()

            total_count = len(behaviors)
            action_type_counts = {}
            total_duration = 0
            active_dates = set()
            daily_counts = {}

            for b in behaviors:
                action_type_counts[b.action_type] = action_type_counts.get(b.action_type, 0) + 1
                total_duration += (b.duration_seconds or 0)
                if b.created_at:
                    date_key = b.created_at.date()
                    active_dates.add(date_key)
                    daily_counts[date_key.isoformat()] = daily_counts.get(date_key.isoformat(), 0) + 1

            return {
                "total_count": total_count,
                "action_types": action_type_counts,
                "total_duration_minutes": round(total_duration / 60, 1),
                "active_days": len(active_dates),
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
