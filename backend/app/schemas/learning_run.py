from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field

class LearningRunCreate(BaseModel):
    chapter_id: int
    plan_version: int = 1
    personalization_snapshot: dict = Field(default_factory=dict)
class PracticeAttemptCreate(BaseModel):
    knowledge_point_id: int
    attempt_number: int = Field(default=1, ge=1)
    is_correct: bool | None = None
    viewed_explanation: bool = False
    misconception_tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
class StageCompletion(BaseModel):
    evidence: dict = Field(default_factory=dict)
class AssessmentItemSubmission(BaseModel):
    item_id: str
    knowledge_point_id: int
    is_correct: bool
    score: float = Field(ge=0, le=1)
    metadata: dict = Field(default_factory=dict)
class AssessmentSubmission(BaseModel):
    submission_key: str = Field(min_length=1, max_length=100)
    items: list[AssessmentItemSubmission] = Field(min_length=1)
class LearningRunResponse(BaseModel):
    id: int; chapter_id: int; status: str; current_stage: str; plan_version: int
    personalization_snapshot: dict; lock_reason: dict | None; stages: list[dict]
    started_at: datetime | None; completed_at: datetime | None
class FeedbackResponse(BaseModel):
    result: str; mastered: list[dict]; weak: list[dict]; next_action: dict; assessment_attempt_id: int
