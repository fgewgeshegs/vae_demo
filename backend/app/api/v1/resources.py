"""学习资源 API"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.learning_resource import LearningResource
from app.schemas.learning_resource import LearningResourceCreate, LearningResourceResponse, ResourceType

router = APIRouter()


@router.get("/", response_model=list[LearningResourceResponse])
async def list_resources(
    course_id: int | None = Query(None),
    resource_type: ResourceType | None = Query(None),
    chapter_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取学习资源列表（支持筛选，返回所有可见资源）"""
    query = select(LearningResource)

    if course_id:
        query = query.where(LearningResource.course_id == course_id)
    if resource_type:
        query = query.where(LearningResource.resource_type == resource_type.value)
    if chapter_id:
        query = query.where(LearningResource.chapter_id == chapter_id)

    query = query.order_by(LearningResource.created_at.desc())
    result = await db.execute(query)
    resources = result.scalars().all()
    return [LearningResourceResponse.model_validate(r) for r in resources]


@router.get("/{resource_id}", response_model=LearningResourceResponse)
async def get_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取资源详情"""
    result = await db.execute(
        select(LearningResource).where(
            LearningResource.id == resource_id,
            LearningResource.user_id == current_user.id,
        )
    )
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    return LearningResourceResponse.model_validate(resource)
