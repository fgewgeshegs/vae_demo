"""智能辅导 API"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.llm_gateway import get_llm_gateway, LLMGateway
from app.models.user import User
from app.models.qa_record import QARecord
from app.schemas.qa_record import QARecordCreate, QARecordResponse

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
    """提问并获取回答"""
    # 调用 LLM
    response = await llm.chat(
        messages=[{"role": "user", "content": data.question}],
        system_prompt="你是一个 AI 学习助手，帮助学习者理解知识点。请用中文回答，结合费曼学习法，引导式解答。",
        temperature=0.7,
    )

    # 保存记录
    record = QARecord(
        user_id=current_user.id,
        course_id=data.course_id,
        question=data.question,
        answer=response.content,
        metadata=data.metadata,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return QARecordResponse.model_validate(record)


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
