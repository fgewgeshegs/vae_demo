"""学习路径 API"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.study_path import StudyPath
from app.schemas.study_path import StudyPathResponse, StudyPathUpdate
from app.services.event_service import EventService, EventType

router = APIRouter()


@router.get("/", response_model=list[StudyPathResponse])
async def list_study_paths(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的学习路径列表"""
    result = await db.execute(
        select(StudyPath)
        .where(StudyPath.user_id == current_user.id)
        .order_by(StudyPath.created_at.desc())
    )
    paths = result.scalars().all()
    return [StudyPathResponse.model_validate(p) for p in paths]


@router.get("/{path_id}", response_model=StudyPathResponse)
async def get_study_path(
    path_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取学习路径详情"""
    result = await db.execute(
        select(StudyPath).where(
            StudyPath.id == path_id,
            StudyPath.user_id == current_user.id,
        )
    )
    path = result.scalar_one_or_none()
    if not path:
        raise HTTPException(status_code=404, detail="学习路径不存在")
    return StudyPathResponse.model_validate(path)


@router.put("/{path_id}", response_model=StudyPathResponse)
async def update_study_path(
    path_id: int,
    data: StudyPathUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新学习路径"""
    result = await db.execute(
        select(StudyPath).where(
            StudyPath.id == path_id,
            StudyPath.user_id == current_user.id,
        )
    )
    path = result.scalar_one_or_none()
    if not path:
        raise HTTPException(status_code=404, detail="学习路径不存在")

    update_data = data.model_dump(exclude_unset=True)
    previous_nodes = path.path_data.get("nodes", []) if path.path_data else []
    previous_completed = {
        index
        for index, node in enumerate(previous_nodes)
        if isinstance(node, dict) and node.get("status") == "completed"
    }
    for key, value in update_data.items():
        setattr(path, key, value)
    await db.flush()
    await db.commit()
    await db.refresh(path)
    updated_nodes = path.path_data.get("nodes", []) if path.path_data else []
    newly_completed = [
        (index, node)
        for index, node in enumerate(updated_nodes)
        if (
            isinstance(node, dict)
            and node.get("status") == "completed"
            and index not in previous_completed
        )
    ]
    for index, node in newly_completed:
        await EventService.emit(
            user_id=current_user.id,
            course_id=path.course_id,
            event_type=EventType.NODE_COMPLETED,
            source_agent="StudyPathAPI",
            target_type="study_path",
            target_id=path.id,
            payload={
                "node_index": index,
                "node": node,
                "progress": path.progress,
            },
        )
    return StudyPathResponse.model_validate(path)
