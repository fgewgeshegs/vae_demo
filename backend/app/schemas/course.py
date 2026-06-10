"""课程与章节 Pydantic Schemas"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CourseCreate(BaseModel):
    title: str = Field(..., max_length=200, description="课程标题")
    description: str | None = Field(None, description="课程描述")
    cover_url: str | None = None
    seed_course: bool = False


class CourseResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    cover_url: str | None = None
    seed_course: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    chapters: list["ChapterResponse"] | None = None

    model_config = ConfigDict(from_attributes=True)


class ChapterCreate(BaseModel):
    course_id: int
    title: str = Field(..., max_length=200)
    description: str | None = None
    sort_order: int = 0


class ChapterResponse(BaseModel):
    id: int
    course_id: int
    title: str
    description: str | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
