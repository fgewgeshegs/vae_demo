"""学习资源 Pydantic Schemas"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class ResourceType(str, Enum):
    DOCUMENT = "document"
    MINDMAP = "mindmap"
    EXERCISE = "exercise"
    CODE = "code"
    READING = "reading"
    VIDEO = "video"


class LearningResourceCreate(BaseModel):
    user_id: int
    course_id: int
    chapter_id: int | None = None
    knowledge_point_id: int | None = None
    resource_type: ResourceType
    title: str = Field(..., max_length=200)
    content: str | None = None
    metadata: dict = Field(default_factory=dict)


class LearningResourceResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    chapter_id: int | None = None
    knowledge_point_id: int | None = None
    resource_type: str
    title: str
    content: str | None = None
    metadata: dict | None = Field(None, validation_alias="resource_metadata")
    is_generated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
