"""学习评估 API"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.evaluation import Evaluation
from app.schemas.evaluation import EvaluationResponse
from app.agents.eval_agent import EvalAgent
from app.services.behavior_service import BehaviorService, ActionType

router = APIRouter()


@router.get("/", response_model=list[EvaluationResponse])
async def list_evaluations(
    course_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取评估报告列表"""
    query = select(Evaluation).where(Evaluation.user_id == current_user.id)
    if course_id:
        query = query.where(Evaluation.course_id == course_id)
    query = query.order_by(Evaluation.created_at.desc())
    result = await db.execute(query)
    evals = result.scalars().all()
    return [EvaluationResponse.model_validate(e) for e in evals]


@router.get("/latest", response_model=EvaluationResponse)
async def get_latest_evaluation(
    course_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取最新评估报告"""
    query = select(Evaluation).where(Evaluation.user_id == current_user.id)
    if course_id:
        query = query.where(Evaluation.course_id == course_id)
    query = query.order_by(Evaluation.created_at.desc()).limit(1)
    result = await db.execute(query)
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise HTTPException(status_code=404, detail="暂无评估数据")
    return EvaluationResponse.model_validate(evaluation)


@router.post("/generate", response_model=dict)
async def generate_evaluation(
    course_id: int | None = None,
    current_user: User = Depends(get_current_user),
):
    """生成学习评估报告"""
    agent = EvalAgent()
    result = await agent.process({
        "user_id": current_user.id,
        "course_id": course_id,
        "message": "生成评估",
    })

    # 记录行为
    if result.get("evaluation"):
        await BehaviorService.record(
            user_id=current_user.id,
            action_type=ActionType.GENERATE_EVALUATION,
            target_type="evaluation",
            target_id=result["evaluation"].get("id"),
            metadata={"course_id": course_id},
        )

    return result


@router.get("/{eval_id}", response_model=EvaluationResponse)
async def get_evaluation(
    eval_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取评估详情"""
    result = await db.execute(
        select(Evaluation).where(
            Evaluation.id == eval_id,
            Evaluation.user_id == current_user.id,
        )
    )
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise HTTPException(status_code=404, detail="评估不存在")
    return EvaluationResponse.model_validate(evaluation)
