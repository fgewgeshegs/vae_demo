"""对话 Agent API - 统一入口

所有用户请求都由 DeepSeek 主 Agent 理解，并自主调用 RAG、画像、路径、资源和评估工具。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.user import User
from app.agents.chat_coordinator import chat_coordinator
from app.services.behavior_service import BehaviorService, ActionType
from loguru import logger
from app.services.retrieval_errors import RetrievalUnavailableError
from app.agents.qa_agent import QAAgent
from app.services.sse import sse_event

router = APIRouter()


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    course_id: int | None = None


@router.post("/")
async def chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    统一对话入口 - 所有用户请求都经过 Coordinator Agent 处理。

    DeepSeek 主 Agent 会根据任务自主选择工具，并基于工具结果组织最终回复。
    """
    logger.info(f"Chat request: user_id={current_user.id}, message={req.message[:50]}...")

    try:
        result = await chat_coordinator.process(
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
        if isinstance(e, RetrievalUnavailableError):
            raise
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    async def events():
        try:
            async for event in QAAgent().stream(
                {
                    "user_id": current_user.id,
                    "course_id": req.course_id,
                    "message": req.message,
                }
            ):
                yield sse_event(event, event.get("type"))
            await BehaviorService.record(
                user_id=current_user.id,
                action_type=ActionType.ASK_QUESTION,
                target_type="chat_stream",
                target_id=current_user.id,
                metadata={"course_id": req.course_id},
            )
        except Exception as exc:
            logger.exception(f"Streaming chat failed: {exc}")
            yield sse_event(
                {"type": "error", "detail": str(exc)},
                "error",
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/agent_stream")
async def chat_agent_stream(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    SSE streaming endpoint for the global Agent.
    Same as /chat/ but uses the streaming coordinator to emit real-time
    thinking process events (thinking steps, tool calls, final answer).
    """
    async def events():
        try:
            async for event in chat_coordinator.stream(
                user_id=current_user.id,
                course_id=req.course_id,
                message=req.message,
            ):
                yield sse_event(event, event.get("type"))

            await BehaviorService.record(
                user_id=current_user.id,
                action_type=ActionType.ASK_QUESTION,
                target_type="chat_agent_stream",
                target_id=current_user.id,
                metadata={"course_id": req.course_id},
            )
        except Exception as exc:
            logger.exception(f"Agent streaming chat failed: {exc}")
            yield sse_event(
                {"type": "error", "detail": str(exc)},
                "error",
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

