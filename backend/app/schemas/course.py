"""璇剧▼涓庣珷鑺?Pydantic Schemas"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.knowledge_point import KnowledgePointResponse


class CourseCreate(BaseModel):
    title: str = Field(..., max_length=200, description="璇剧▼鏍囬")
    description: str | None = Field(None, description="璇剧▼鎻忚堪")
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
    knowledge_points: list[KnowledgePointResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
