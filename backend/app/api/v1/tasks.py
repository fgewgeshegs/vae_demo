"""Explicit learning task API."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.learning_task import LearningTask
from app.models.user import User
from app.schemas.learning_task import LearningTaskCreate, LearningTaskResponse
from app.services.learning_task_service import LearningTaskService

router = APIRouter()


@router.post("/", response_model=LearningTaskResponse)
async def create_learning_task(
    data: LearningTaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a deterministic learning task and execute it in the background."""
    task = await LearningTaskService.create_task(
        db,
        task_type=data.task_type,
        user_id=current_user.id,
        course_id=data.course_id,
        input_data=data.input,
    )
    background_tasks.add_task(LearningTaskService.run_task, task.id)
    return LearningTaskResponse.model_validate(task)


@router.get("/", response_model=list[LearningTaskResponse])
async def list_learning_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(LearningTask)
        .where(LearningTask.user_id == current_user.id)
        .order_by(LearningTask.created_at.desc())
    )
    return [LearningTaskResponse.model_validate(task) for task in result.scalars().all()]


@router.get("/{task_id}", response_model=LearningTaskResponse)
async def get_learning_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(LearningTask).where(
            LearningTask.id == task_id,
            LearningTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Learning task not found")
    return LearningTaskResponse.model_validate(task)
