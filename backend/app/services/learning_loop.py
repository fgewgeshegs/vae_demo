"""Deterministic first-stage learning-loop rules. This module never calls an LLM."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.course import Chapter
from app.models.knowledge_point import KnowledgePoint
from app.models.learning_run import AssessmentAttempt, AssessmentItemResult, ChapterLearningRun, ChapterLearningStage, KnowledgePointDependency, KnowledgePointMastery, MasteryHistory, PracticeAttempt

STAGES = ("learn", "practice", "assess", "feedback", "review", "remedial")
PASS_THRESHOLD = 0.70

def feedback_for_mastery(values: dict[int, float]) -> dict:
    mastered = [{"knowledge_point_id": key, "mastery": value} for key, value in values.items() if value >= PASS_THRESHOLD]
    weak = [{"knowledge_point_id": key, "mastery": value} for key, value in values.items() if value < PASS_THRESHOLD]
    if weak:
        return {"result": "partial_mastery", "mastered": mastered, "weak": weak, "next_action": {"type": "remedial", "reason": f"{len(weak)} knowledge point(s) below 70%"}}
    return {"result": "mastered", "mastered": mastered, "weak": [], "next_action": {"type": "review", "reason": "Assessment threshold met; schedule a retention review."}}

class LearningLoopService:
    async def complete_stage(self, db: AsyncSession, run: ChapterLearningRun, stage: str, evidence: dict) -> None:
        transitions = {"learn": "practice", "practice": "assess"}
        if stage not in transitions or run.current_stage != stage:
            raise HTTPException(409, f"Cannot complete {stage} during {run.current_stage}")
        now = datetime.now(timezone.utc)
        rows = (await db.execute(select(ChapterLearningStage).where(ChapterLearningStage.run_id == run.id))).scalars().all()
        for row in rows:
            if row.stage == stage:
                row.status, row.evidence, row.completed_at = "completed", evidence, now
            elif row.stage == transitions[stage]:
                row.status, row.started_at = "active", now
        run.current_stage = transitions[stage]

    async def create_run(self, db: AsyncSession, user_id: int, chapter_id: int, plan_version: int, snapshot: dict) -> ChapterLearningRun:
        if not (await db.execute(select(Chapter.id).where(Chapter.id == chapter_id))).scalar_one_or_none():
            raise HTTPException(404, "Chapter not found")
        existing = (await db.execute(
            select(ChapterLearningRun)
            .where(
                ChapterLearningRun.user_id == user_id,
                ChapterLearningRun.chapter_id == chapter_id,
                ChapterLearningRun.status != "completed",
            )
            .order_by(ChapterLearningRun.id.desc())
        )).scalars().first()
        if existing:
            return existing
        blocked = await self._blocked(db, user_id, chapter_id)
        reason = None if not blocked else {"reason_code": "prerequisite_not_met", "blocked_by": blocked, "unlock_condition": "Prerequisite mastery must reach 70%"}
        run = ChapterLearningRun(user_id=user_id, chapter_id=chapter_id, plan_version=plan_version, personalization_snapshot=snapshot, status="locked" if blocked else "active", current_stage="locked" if blocked else "learn", lock_reason=reason)
        db.add(run); await db.flush()
        now = datetime.now(timezone.utc)
        for stage in STAGES:
            db.add(ChapterLearningStage(run_id=run.id, stage=stage, status="active" if stage == "learn" and not blocked else "locked", started_at=now if stage == "learn" and not blocked else None))
        await db.flush(); return run

    async def add_practice_attempt(self, db: AsyncSession, run: ChapterLearningRun, data) -> PracticeAttempt:
        self._require(run, ("practice", "remedial")); await self._assert_kp(db, run.chapter_id, data.knowledge_point_id)
        attempt = PracticeAttempt(run_id=run.id, knowledge_point_id=data.knowledge_point_id, attempt_number=data.attempt_number, is_correct=data.is_correct, viewed_explanation=data.viewed_explanation, misconception_tags=data.misconception_tags, metadata_=data.metadata)
        db.add(attempt); return attempt

    async def submit_assessment(self, db: AsyncSession, run: ChapterLearningRun, data) -> AssessmentAttempt:
        self._require(run, ("assess", "remedial"))
        existing = (await db.execute(select(AssessmentAttempt).where(AssessmentAttempt.run_id == run.id, AssessmentAttempt.submission_key == data.submission_key))).scalar_one_or_none()
        if existing: return existing
        for item in data.items: await self._assert_kp(db, run.chapter_id, item.knowledge_point_id)
        groups: dict[int, list[float]] = defaultdict(list)
        for item in data.items: groups[item.knowledge_point_id].append(item.score)
        assessment = AssessmentAttempt(run_id=run.id, submission_key=data.submission_key, total_score=sum(item.score for item in data.items) / len(data.items), passed=all(sum(v)/len(v) >= PASS_THRESHOLD for v in groups.values()))
        db.add(assessment); await db.flush()
        for item in data.items: db.add(AssessmentItemResult(assessment_attempt_id=assessment.id, knowledge_point_id=item.knowledge_point_id, item_id=item.item_id, is_correct=item.is_correct, score=item.score, metadata_=item.metadata))
        changed = {}
        for kp_id, scores in groups.items():
            evidence = sum(scores) / len(scores)
            mastery = (await db.execute(select(KnowledgePointMastery).where(KnowledgePointMastery.user_id == run.user_id, KnowledgePointMastery.knowledge_point_id == kp_id))).scalar_one_or_none()
            old = mastery.mastery if mastery else 0.0; new = evidence if mastery is None else round(old * 0.4 + evidence * 0.6, 4)
            if mastery is None:
                mastery = KnowledgePointMastery(user_id=run.user_id, knowledge_point_id=kp_id, mastery=new, last_evidence_at=datetime.now(timezone.utc)); db.add(mastery); await db.flush()
            else: mastery.mastery, mastery.last_evidence_at = new, datetime.now(timezone.utc)
            db.add(MasteryHistory(mastery_id=mastery.id, source_type="assessment", source_id=assessment.id, old_mastery=old, new_mastery=new, reason={"assessment_score": evidence, "knowledge_point_id": kp_id}))
            changed[kp_id] = new
        assessment.feedback = feedback_for_mastery(changed); await self._advance(db, run, assessment.feedback); return assessment

    async def latest_feedback(self, db: AsyncSession, run: ChapterLearningRun) -> AssessmentAttempt:
        row = (await db.execute(select(AssessmentAttempt).where(AssessmentAttempt.run_id == run.id).order_by(AssessmentAttempt.id.desc()))).scalars().first()
        if not row: raise HTTPException(409, "No assessment has been submitted for this learning run")
        return row

    async def _blocked(self, db: AsyncSession, user_id: int, chapter_id: int) -> list[int]:
        dependencies = (await db.execute(select(KnowledgePointDependency.prerequisite_knowledge_point_id, KnowledgePointDependency.required_mastery_threshold).join(KnowledgePoint, KnowledgePoint.id == KnowledgePointDependency.knowledge_point_id).where(KnowledgePoint.chapter_id == chapter_id))).all()
        if not dependencies: return []
        ids = [row[0] for row in dependencies]
        found = (await db.execute(select(KnowledgePointMastery).where(KnowledgePointMastery.user_id == user_id, KnowledgePointMastery.knowledge_point_id.in_(ids)))).scalars().all()
        values = {row.knowledge_point_id: row.mastery for row in found}
        return [kp_id for kp_id, threshold in dependencies if values.get(kp_id, 0.0) < threshold]

    async def _assert_kp(self, db: AsyncSession, chapter_id: int, kp_id: int) -> None:
        if not (await db.execute(select(KnowledgePoint.id).where(KnowledgePoint.id == kp_id, KnowledgePoint.chapter_id == chapter_id))).scalar_one_or_none(): raise HTTPException(422, "Knowledge point does not belong to this chapter")
    def _require(self, run: ChapterLearningRun, allowed: tuple[str, ...]) -> None:
        if run.status == "locked": raise HTTPException(409, detail=run.lock_reason)
        if run.current_stage not in allowed: raise HTTPException(409, f"Action is unavailable during {run.current_stage}")
    async def _advance(self, db: AsyncSession, run: ChapterLearningRun, feedback: dict) -> None:
        next_stage, now = feedback["next_action"]["type"], datetime.now(timezone.utc); run.current_stage = next_stage
        for row in (await db.execute(select(ChapterLearningStage).where(ChapterLearningStage.run_id == run.id))).scalars():
            if row.stage == "assess": row.status, row.completed_at = "completed", now
            elif row.stage == "feedback": row.status, row.evidence, row.completed_at = "completed", feedback, now
            elif row.stage == next_stage: row.status, row.started_at = "active", now
