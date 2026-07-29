"""Service layer for explicit learning tasks."""

from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.workflow_coordinator import workflow_coordinator
from app.core.database import async_session_factory
from app.models.learning_task import LearningTask
from app.services.behavior_service import ActionType, BehaviorService


class LearningTaskService:
    """Create a durable task record before invoking deterministic agent work."""

    @staticmethod
    async def create_task(
        db: AsyncSession,
        *,
        task_type: str,
        user_id: int,
        course_id: int | None,
        input_data: dict[str, Any] | None = None,
    ) -> LearningTask:
        task = LearningTask(
            task_type=task_type,
            user_id=user_id,
            course_id=course_id,
            status="running",
            input=input_data or {},
            steps=[
                {"name": "task_created", "status": "done", "label": "任务已创建"},
                {"name": "workflow_started", "status": "running", "label": "正在启动学习任务"},
            ],
            result={},
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    async def run_task(task_id: int) -> None:
        async with async_session_factory() as db:
            result = await db.execute(select(LearningTask).where(LearningTask.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                logger.warning(f"Learning task not found for background run: id={task_id}")
                return

            async def emit_step(step: dict[str, Any]) -> None:
                await LearningTaskService._append_step(db, task, step)

            try:
                await emit_step({
                    "name": "workflow_started",
                    "status": "done",
                    "label": "学习任务已启动",
                })
                workflow_result = await workflow_coordinator.run(task, emit_step=emit_step)
                task.status = workflow_result.get("status", "succeeded")
                task.result = workflow_result or {}
                task.error = None if task.status == "succeeded" else workflow_result.get("message", "Workflow failed")
                task.steps = [
                    *LearningTaskService._replace_step(
                        task.steps,
                        {
                            "name": "task_completed",
                            "status": "done" if task.status == "succeeded" else "failed",
                            "label": "任务完成" if task.status == "succeeded" else "任务失败",
                            "error": task.error,
                        },
                    )
                ]
                await db.commit()
            except Exception as exc:
                logger.exception(f"Learning task failed: id={task.id}, type={task.task_type}")
                task.status = "failed"
                task.error = str(exc)
                task.result = {"message": str(exc)}
                task.steps = LearningTaskService._replace_step(
                    task.steps,
                    {
                        "name": "task_completed",
                        "status": "failed",
                        "label": "任务失败",
                        "error": str(exc),
                    },
                )
                await db.commit()

            await BehaviorService.record(
                user_id=task.user_id,
                action_type=ActionType.RUN_LEARNING_TASK,
                target_type="learning_task",
                target_id=task.id,
                metadata={
                    "task_type": task.task_type,
                    "course_id": task.course_id,
                    "status": task.status,
                },
            )

    @staticmethod
    async def create_and_run(
        db: AsyncSession,
        *,
        task_type: str,
        user_id: int,
        course_id: int | None,
        input_data: dict[str, Any] | None = None,
    ) -> LearningTask:
        task = LearningTask(
            task_type=task_type,
            user_id=user_id,
            course_id=course_id,
            status="running",
            input=input_data or {},
            steps=[{"name": "task_created", "status": "done"}],
            result={},
        )
        db.add(task)
        await db.flush()

        try:
            task.steps = [*task.steps, {"name": "workflow_started", "status": "running"}]
            result = await workflow_coordinator.run(task)
            task.status = result.get("status", "succeeded")
            task.result = result or {}
            task.steps = [
                {"name": "task_created", "status": "done"},
                {"name": "workflow_started", "status": "done"},
                *result.get("steps", []),
                {
                    "name": "task_completed",
                    "status": "done" if task.status == "succeeded" else "failed",
                },
            ]
            if task.status != "succeeded":
                task.error = result.get("message", "Workflow failed")
            await db.flush()
        except Exception as exc:
            logger.exception(f"Learning task failed: id={task.id}, type={task_type}")
            task.status = "failed"
            task.error = str(exc)
            task.result = {"message": str(exc)}
            task.steps = [
                *task.steps,
                {"name": "agent_started", "status": "failed", "error": str(exc)},
            ]
            await db.flush()

        await db.commit()
        await db.refresh(task)
        await BehaviorService.record(
            user_id=user_id,
            action_type=ActionType.RUN_LEARNING_TASK,
            target_type="learning_task",
            target_id=task.id,
            metadata={
                "task_type": task_type,
                "course_id": course_id,
                "status": task.status,
            },
        )
        return task

    @staticmethod
    async def _append_step(db: AsyncSession, task: LearningTask, step: dict[str, Any]) -> None:
        task.steps = LearningTaskService._replace_step(task.steps, step)
        await db.commit()
        await db.refresh(task)

    @staticmethod
    def _replace_step(steps: list[dict[str, Any]] | list[Any], step: dict[str, Any]) -> list[dict[str, Any]]:
        clean_steps = [item for item in steps if isinstance(item, dict)]
        name = step.get("name")
        if name:
            clean_steps = [item for item in clean_steps if item.get("name") != name]
        clean_steps.append({key: value for key, value in step.items() if value is not None})
        return clean_steps
