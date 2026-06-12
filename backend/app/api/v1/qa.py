"""智能辅导 API"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.llm_gateway import get_llm_gateway, LLMGateway
from app.models.user import User
from app.models.qa_record import QARecord
from app.schemas.qa_record import QARecordCreate, QARecordResponse
from app.agents.qa_agent import QAAgent
from app.services.behavior_service import BehaviorService, ActionType

router = APIRouter()


@router.get("/", response_model=list[QARecordResponse])
async def list_qa_records(
    course_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取问答历史"""
    query = select(QARecord).where(QARecord.user_id == current_user.id)
    if course_id:
        query = query.where(QARecord.course_id == course_id)
    query = query.order_by(QARecord.created_at.desc()).limit(50)
    result = await db.execute(query)
    records = result.scalars().all()
    return [QARecordResponse.model_validate(r) for r in records]


@router.post("/ask", response_model=QARecordResponse)
async def ask_question(
    data: QARecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm: LLMGateway = Depends(get_llm_gateway),
):
    """提问并获取回答（使用 QAAgent 进行画像感知的回答）"""
    # 使用 QAAgent 获取画像感知的回答
    qa_agent = QAAgent()
    agent_result = await qa_agent.process({
        "user_id": current_user.id,
        "course_id": data.course_id,
        "message": data.question,
    })

    answer = agent_result.get("answer", "")

    # 保存记录
    record = QARecord(
        user_id=current_user.id,
        course_id=data.course_id,
        question=data.question,
        answer=answer,
        qa_metadata=data.metadata,
    )
    db.add(record)
    await db.flush()
    await db.commit()
    await db.refresh(record)

    # 记录行为
    await BehaviorService.record(
        user_id=current_user.id,
        action_type=ActionType.ASK_QUESTION,
        target_type="qa_record",
        target_id=record.id,
        metadata={"course_id": data.course_id},
    )

    return QARecordResponse.model_validate(record)


@router.get("/count")
async def count_qa_records(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的问答记录总数"""
    query = select(func.count()).select_from(QARecord).where(QARecord.user_id == current_user.id)
    result = await db.execute(query)
    count = result.scalar()
    return {"count": count}


@router.get("/{record_id}", response_model=QARecordResponse)
async def get_qa_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取问答详情"""
    result = await db.execute(
        select(QARecord).where(
            QARecord.id == record_id,
            QARecord.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return QARecordResponse.model_validate(record)
