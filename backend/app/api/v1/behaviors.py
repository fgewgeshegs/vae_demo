"""学习行为 API - 记录和查询学习行为"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.behavior_service import BehaviorService, ActionType

router = APIRouter()


@router.post("/record", response_model=dict)
async def record_behavior(
    action_type: str = Query(..., description="行为类型"),
    target_type: str | None = Query(None, description="目标类型"),
    target_id: int | None = Query(None, description="目标ID"),
    duration_seconds: int = Query(0, description="持续秒数"),
    current_user: User = Depends(get_current_user),
):
    """记录学习行为"""
    behavior = await BehaviorService.record(
        user_id=current_user.id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        duration_seconds=duration_seconds,
    )
    if behavior:
        return {"success": True, "id": behavior.id}
    return {"success": False, "error": "记录失败"}


@router.get("/stats", response_model=dict)
async def get_behavior_stats(
    current_user: User = Depends(get_current_user),
):
    """获取行为统计"""
    stats = await BehaviorService.get_user_stats(current_user.id)
    return stats


@router.get("/recent", response_model=list[dict])
async def get_recent_activities(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """获取最近活动"""
    activities = await BehaviorService.get_recent_activities(
        user_id=current_user.id,
        limit=limit,
    )
    return activities
