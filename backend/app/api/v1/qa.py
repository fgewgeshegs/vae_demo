"""智能辅导 API"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.qa_record import QARecord
from app.schemas.qa_record import QARecordCreate, QARecordResponse
from app.agents.qa_agent import QAAgent
from app.services.behavior_service import BehaviorService, ActionType
from app.services.event_service import EventService, EventType

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
):
    """提问并获取回答（使用 QAAgent 进行画像感知的回答）"""
    conversation_id = data.conversation_id or str(uuid4())
    history: list[dict[str, str]] = []
    if data.conversation_id:
        if data.conversation_id.startswith("legacy-"):
            try:
                legacy_record_id = int(data.conversation_id.removeprefix("legacy-"))
            except ValueError as exc:
                raise HTTPException(status_code=404, detail="会话不存在") from exc
            legacy_result = await db.execute(
                select(QARecord).where(
                    QARecord.id == legacy_record_id,
                    QARecord.user_id == current_user.id,
                    QARecord.conversation_id.is_(None),
                )
            )
            legacy_record = legacy_result.scalar_one_or_none()
            if not legacy_record:
                raise HTTPException(status_code=404, detail="会话不存在")
            conversation_id = str(uuid4())
            legacy_record.conversation_id = conversation_id
            previous_records = [legacy_record]
        else:
            history_result = await db.execute(
                select(QARecord)
                .where(
                    QARecord.user_id == current_user.id,
                    QARecord.conversation_id == data.conversation_id,
                )
                .order_by(QARecord.created_at.desc())
                .limit(8)
            )
            previous_records = list(reversed(history_result.scalars().all()))
        if not previous_records:
            raise HTTPException(status_code=404, detail="会话不存在")
        history = [
            message
            for record in previous_records
            for message in (
                {"role": "user", "content": record.question},
                *([{ "role": "assistant", "content": record.answer }] if record.answer else []),
            )
        ]

    # 使用 QAAgent 获取画像感知的回答
    qa_agent = QAAgent()
    agent_result = await qa_agent.process({
        "user_id": current_user.id,
        "course_id": data.course_id,
        "message": data.question,
        "mode": (data.metadata or {}).get("mode", "expert"),
        "history": history,
    })

    answer = agent_result.get("answer", "")

    # 保存记录
    qa_metadata = dict(data.metadata or {})
    qa_metadata.update({
        "provider": agent_result.get("provider"),
        "retrieval_method": agent_result.get("retrieval_method"),
        "sources": agent_result.get("sources", []),
    })

    record = QARecord(
        user_id=current_user.id,
        course_id=data.course_id,
        question=data.question,
        answer=answer,
        conversation_id=conversation_id,
        qa_metadata=qa_metadata,
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
    await EventService.emit(
        user_id=current_user.id,
        course_id=data.course_id,
        event_type=EventType.QA_ANSWERED,
        source_agent="QAAgent",
        target_type="qa_record",
        target_id=record.id,
        payload={
            "question": data.question,
            "provider": agent_result.get("provider"),
            "retrieval_method": agent_result.get("retrieval_method"),
            "source_count": len(agent_result.get("sources", [])),
        },
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
