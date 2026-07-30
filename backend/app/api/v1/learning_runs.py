from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.learning_run import ChapterLearningRun, ChapterLearningStage
from app.models.user import User
from app.schemas.learning_run import AssessmentSubmission, FeedbackResponse, LearningRunCreate, LearningRunResponse, PracticeAttemptCreate, StageCompletion
from app.services.learning_loop import LearningLoopService
router = APIRouter(); service = LearningLoopService()
def response(run, stages): return LearningRunResponse(id=run.id, chapter_id=run.chapter_id, status=run.status, current_stage=run.current_stage, plan_version=run.plan_version, personalization_snapshot=run.personalization_snapshot, lock_reason=run.lock_reason, started_at=run.started_at, completed_at=run.completed_at, stages=[{"stage": s.stage, "status": s.status, "evidence": s.evidence, "started_at": s.started_at, "completed_at": s.completed_at} for s in stages])
async def get_run(run_id, db, user_id):
    run = (await db.execute(select(ChapterLearningRun).where(ChapterLearningRun.id == run_id, ChapterLearningRun.user_id == user_id))).scalar_one_or_none()
    if not run: raise HTTPException(404, "Learning run not found")
    return run
@router.post("/", response_model=LearningRunResponse, status_code=status.HTTP_201_CREATED)
async def create(data: LearningRunCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    run = await service.create_run(db, current_user.id, data.chapter_id, data.plan_version, data.personalization_snapshot); stages = (await db.execute(select(ChapterLearningStage).where(ChapterLearningStage.run_id == run.id).order_by(ChapterLearningStage.id))).scalars().all(); return response(run, stages)
@router.get("/{run_id}", response_model=LearningRunResponse)
async def read(run_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    run = await get_run(run_id, db, current_user.id); stages = (await db.execute(select(ChapterLearningStage).where(ChapterLearningStage.run_id == run.id).order_by(ChapterLearningStage.id))).scalars().all(); return response(run, stages)
@router.post("/{run_id}/learning-completions", status_code=status.HTTP_204_NO_CONTENT)
async def complete_learning(run_id: int, data: StageCompletion, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    run = await get_run(run_id, db, current_user.id); await service.complete_stage(db, run, "learn", data.evidence)
@router.post("/{run_id}/practice-completions", status_code=status.HTTP_204_NO_CONTENT)
async def complete_practice(run_id: int, data: StageCompletion, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    run = await get_run(run_id, db, current_user.id); await service.complete_stage(db, run, "practice", data.evidence)
@router.post("/{run_id}/practice-attempts", status_code=status.HTTP_201_CREATED)
async def practice(run_id: int, data: PracticeAttemptCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    run = await get_run(run_id, db, current_user.id); row = await service.add_practice_attempt(db, run, data); await db.flush(); return {"id": row.id, "run_id": run.id, "knowledge_point_id": row.knowledge_point_id}
@router.post("/{run_id}/assessments", response_model=FeedbackResponse)
async def assess(run_id: int, data: AssessmentSubmission, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    run = await get_run(run_id, db, current_user.id); row = await service.submit_assessment(db, run, data); return FeedbackResponse(assessment_attempt_id=row.id, **row.feedback)
@router.get("/{run_id}/feedback", response_model=FeedbackResponse)
async def feedback(run_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    run = await get_run(run_id, db, current_user.id); row = await service.latest_feedback(db, run); return FeedbackResponse(assessment_attempt_id=row.id, **row.feedback)
