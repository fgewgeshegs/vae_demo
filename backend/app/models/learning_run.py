"""Persistent models for the deterministic chapter learning loop."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class ChapterLearningRun(Base):
    __tablename__ = "chapter_learning_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    current_stage: Mapped[str] = mapped_column(String(20), nullable=False, default="learn")
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    personalization_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    lock_reason: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (CheckConstraint("status IN ('locked', 'active', 'completed')", name="ck_runs_status"), CheckConstraint("current_stage IN ('locked', 'learn', 'practice', 'assess', 'feedback', 'review', 'remedial')", name="ck_runs_stage"), Index("idx_runs_user_chapter", "user_id", "chapter_id"))

class ChapterLearningStage(Base):
    __tablename__ = "chapter_learning_stages"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("chapter_learning_runs.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="locked")
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("run_id", "stage", name="uq_stage_run_stage"), CheckConstraint("stage IN ('learn', 'practice', 'assess', 'feedback', 'review', 'remedial')", name="ck_stage_name"), CheckConstraint("status IN ('locked', 'available', 'active', 'completed')", name="ck_stage_status"), Index("idx_stages_stage_status", "stage", "status"))

class KnowledgePointDependency(Base):
    __tablename__ = "knowledge_point_dependencies"
    knowledge_point_id: Mapped[int] = mapped_column(ForeignKey("knowledge_points.id", ondelete="CASCADE"), primary_key=True)
    prerequisite_knowledge_point_id: Mapped[int] = mapped_column(ForeignKey("knowledge_points.id", ondelete="CASCADE"), primary_key=True)
    dependency_type: Mapped[str] = mapped_column(String(30), nullable=False, default="prerequisite")
    required_mastery_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.70)
    __table_args__ = (CheckConstraint("knowledge_point_id <> prerequisite_knowledge_point_id", name="ck_dependency_self"), CheckConstraint("required_mastery_threshold >= 0 AND required_mastery_threshold <= 1", name="ck_dependency_threshold"))

class KnowledgePointMastery(Base):
    __tablename__ = "knowledge_point_mastery"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    knowledge_point_id: Mapped[int] = mapped_column(ForeignKey("knowledge_points.id", ondelete="CASCADE"), nullable=False)
    mastery: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_evidence_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint("user_id", "knowledge_point_id", name="uq_mastery_user_kp"), CheckConstraint("mastery >= 0 AND mastery <= 1", name="ck_mastery_range"), Index("idx_mastery_user", "user_id"))

class MasteryHistory(Base):
    __tablename__ = "mastery_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    mastery_id: Mapped[int] = mapped_column(ForeignKey("knowledge_point_mastery.id", ondelete="CASCADE"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer)
    old_mastery: Mapped[float] = mapped_column(Float, nullable=False)
    new_mastery: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class PracticeAttempt(Base):
    __tablename__ = "practice_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("chapter_learning_runs.id", ondelete="CASCADE"), nullable=False)
    knowledge_point_id: Mapped[int] = mapped_column(ForeignKey("knowledge_points.id", ondelete="CASCADE"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    viewed_explanation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    misconception_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("chapter_learning_runs.id", ondelete="CASCADE"), nullable=False)
    submission_key: Mapped[str] = mapped_column(String(100), nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feedback: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("run_id", "submission_key", name="uq_assessment_run_key"),)

class AssessmentItemResult(Base):
    __tablename__ = "assessment_item_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_attempt_id: Mapped[int] = mapped_column(ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False)
    knowledge_point_id: Mapped[int] = mapped_column(ForeignKey("knowledge_points.id", ondelete="CASCADE"), nullable=False)
    item_id: Mapped[str] = mapped_column(String(100), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    __table_args__ = (CheckConstraint("score >= 0 AND score <= 1", name="ck_assessment_score"),)
