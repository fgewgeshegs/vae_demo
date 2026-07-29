"""对话式画像构建 API - 通过自然语言对话自动构建学生画像"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.models.user import User
from app.services.profile_conversation_service import ProfileConversationService
from loguru import logger


router = APIRouter()


class StartConversationRequest(BaseModel):
    """开始对话请求"""
    course_id: int | None = Field(None, description="课程ID（可选）")


class ContinueConversationRequest(BaseModel):
    """继续对话请求"""
    conversation_id: str = Field(..., description="对话ID")
    message: str = Field(..., description="用户消息")
    course_id: int | None = Field(None, description="课程ID（可选）")


class EndConversationRequest(BaseModel):
    """结束对话请求"""
    conversation_id: str = Field(..., description="对话ID")


class ConversationResponse(BaseModel):
    """对话响应"""
    type: str
    conversation_id: str | None = None
    message: str
    data: dict | None = None


@router.post("/start", response_model=ConversationResponse)
async def start_conversation(
    req: StartConversationRequest,
    current_user: User = Depends(get_current_user),
):
    """
    开始新的画像构建对话

    通过自然语言对话自动构建学生画像，支持多轮对话，逐步完善画像信息。
    """
    logger.info(f"Start profile conversation: user_id={current_user.id}")

    try:
        service = ProfileConversationService()
        result = await service.start_conversation(
            user_id=current_user.id,
            course_id=req.course_id,
        )

        return ConversationResponse(
            type=result["type"],
            conversation_id=result.get("conversation_id"),
            message=result["message"],
            data={
                "opening_message": result.get("opening_message"),
                "current_profile": result.get("current_profile"),
                "phase": result.get("phase"),
            },
        )
    except Exception as e:
        logger.error(f"Failed to start profile conversation: {e}")
        raise HTTPException(status_code=500, detail=f"启动对话失败: {str(e)}")


@router.post("/continue", response_model=ConversationResponse)
async def continue_conversation(
    req: ContinueConversationRequest,
    current_user: User = Depends(get_current_user),
):
    """
    继续对话并更新画像

    发送用户消息，系统会自动分析消息内容，提取画像信息，并生成回复。
    """
    logger.info(
        f"Continue profile conversation: user_id={current_user.id}, "
        f"conversation_id={req.conversation_id}"
    )

    try:
        service = ProfileConversationService()
        result = await service.continue_conversation(
            user_id=current_user.id,
            conversation_id=req.conversation_id,
            message=req.message,
            course_id=req.course_id,
        )

        return ConversationResponse(
            type=result["type"],
            conversation_id=result.get("conversation_id"),
            message=result["message"],
            data={
                "response": result.get("response"),
                "updated_profile": result.get("updated_profile"),
                "extraction_result": result.get("extraction_result"),
            },
        )
    except Exception as e:
        logger.error(f"Failed to continue profile conversation: {e}")
        raise HTTPException(status_code=500, detail=f"继续对话失败: {str(e)}")


@router.post("/end", response_model=ConversationResponse)
async def end_conversation(
    req: EndConversationRequest,
    current_user: User = Depends(get_current_user),
):
    """
    结束对话并生成最终画像

    结束画像构建对话，返回最终的画像总结。
    """
    logger.info(
        f"End profile conversation: user_id={current_user.id}, "
        f"conversation_id={req.conversation_id}"
    )

    try:
        service = ProfileConversationService()
        result = await service.end_conversation(
            user_id=current_user.id,
            conversation_id=req.conversation_id,
        )

        return ConversationResponse(
            type=result["type"],
            conversation_id=result.get("conversation_id"),
            message=result["message"],
            data={
                "final_profile": result.get("final_profile"),
                "summary": result.get("summary"),
            },
        )
    except Exception as e:
        logger.error(f"Failed to end profile conversation: {e}")
        raise HTTPException(status_code=500, detail=f"结束对话失败: {str(e)}")


@router.get("/suggested-questions")
async def get_suggested_questions(
    current_user: User = Depends(get_current_user),
):
    """
    获取建议问题

    根据当前画像状态，生成建议的对话问题，帮助完善画像信息。
    """
    logger.info(f"Get suggested questions: user_id={current_user.id}")

    try:
        service = ProfileConversationService()
        profile = await service._load_profile(current_user.id)
        questions = await service.get_suggested_questions(
            user_id=current_user.id,
            profile=profile,
        )

        return {
            "type": "suggested_questions",
            "questions": questions,
            "profile_completeness": service._calculate_completeness(profile),
            "message": "建议问题已生成",
        }
    except Exception as e:
        logger.error(f"Failed to get suggested questions: {e}")
        raise HTTPException(status_code=500, detail=f"获取建议问题失败: {str(e)}")
