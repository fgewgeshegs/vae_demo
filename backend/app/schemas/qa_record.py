"""问答记录 Pydantic Schemas"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class QARecordCreate(BaseModel):
    course_id: int | None = None
    question: str = Field(..., description="用户问题")
    metadata: dict = Field(default_factory=dict)


class QARecordResponse(BaseModel):
    id: int
    user_id: int
    course_id: int | None = None
    question: str
    answer: str | None = None
    resource_ids: list[int] | None = None
    metadata: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
