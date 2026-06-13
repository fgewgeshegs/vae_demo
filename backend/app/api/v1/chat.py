"""对话 Agent API - 统一入口

所有用户请求都通过 Coordinator Agent 处理，由 LangGraph 状态图进行意图识别和任务分发。
这是系统的单一入口点，所有功能（画像/资源/路径/问答/评估）都走这里。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.agents.coordinator import coordinator
from app.services.behavior_service import BehaviorService, ActionType
from loguru import logger

router = APIRouter()


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    course_id: int | None = None


@router.post("")
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    统一对话入口 - 所有用户请求都经过 Coordinator Agent 处理。

    Coordinator 会：
    1. 识别用户意图（画像/资源/路径/问答/评估）
    2. 路由到对应的子 Agent
    3. 返回处理结果
    """
    logger.info(f"Chat request: user_id={current_user.id}, message={req.message[:50]}...")

    try:
        result = await coordinator.process(
            user_id=current_user.id,
            course_id=req.course_id,
            message=req.message,
        )

        await BehaviorService.record(
            user_id=current_user.id,
            action_type=ActionType.ASK_QUESTION,
            target_type="chat",
            target_id=current_user.id,
            metadata={
                "intent": result.get("type", "unknown"),
                "course_id": req.course_id,
            },
        )

        return {
            "type": result.get("type", "unknown"),
            "data": result,
            "message": result.get("message", result.get("answer", "处理完成")),
        }

    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")
