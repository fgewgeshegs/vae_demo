"""知识点 API"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.knowledge_point import KnowledgePoint
from app.schemas.knowledge_point import KnowledgePointCreate, KnowledgePointResponse

router = APIRouter()


@router.get("/chapter/{chapter_id}", response_model=list[KnowledgePointResponse])
async def list_knowledge_points(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取章节的知识点列表"""
    result = await db.execute(
        select(KnowledgePoint)
        .where(KnowledgePoint.chapter_id == chapter_id)
        .order_by(KnowledgePoint.sort_order)
    )
    kps = result.scalars().all()
    return [KnowledgePointResponse.model_validate(kp) for kp in kps]


@router.get("/{kp_id}", response_model=KnowledgePointResponse)
async def get_knowledge_point(
    kp_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取知识点详情"""
    result = await db.execute(select(KnowledgePoint).where(KnowledgePoint.id == kp_id))
    kp = result.scalar_one_or_none()
    if not kp:
        raise HTTPException(status_code=404, detail="知识点不存在")
    return KnowledgePointResponse.model_validate(kp)


@router.post("/", response_model=KnowledgePointResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_point(
    data: KnowledgePointCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建知识点"""
    kp = KnowledgePoint(**data.model_dump())
    db.add(kp)
    await db.flush()
    await db.commit()
    await db.refresh(kp)
    return KnowledgePointResponse.model_validate(kp)


@router.delete("/{kp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_point(
    kp_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除知识点"""
    result = await db.execute(select(KnowledgePoint).where(KnowledgePoint.id == kp_id))
    kp = result.scalar_one_or_none()
    if not kp:
        raise HTTPException(status_code=404, detail="知识点不存在")
    await db.delete(kp)
    await db.commit()
