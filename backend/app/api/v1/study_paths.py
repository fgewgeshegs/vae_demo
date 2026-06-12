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
    for key, value in update_data.items():
        setattr(path, key, value)
    await db.flush()
    await db.commit()
    await db.refresh(path)
    return StudyPathResponse.model_validate(path)
