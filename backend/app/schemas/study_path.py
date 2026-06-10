"""学习路径 Pydantic Schemas"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class StudyPathResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    path_data: dict
    progress: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudyPathUpdate(BaseModel):
    path_data: dict | None = None
    progress: float | None = Field(None, ge=0.0, le=1.0)
    is_active: bool | None = None
