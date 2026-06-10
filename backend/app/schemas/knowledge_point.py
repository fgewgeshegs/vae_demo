"""知识点 Pydantic Schemas"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class KnowledgePointCreate(BaseModel):
    chapter_id: int
    title: str = Field(..., max_length=200)
    content: str | None = None
    difficulty: str = Field("medium", pattern=r"^(easy|medium|hard)$")
    prerequisites: list[int] = Field(default_factory=list)
    sort_order: int = 0


class KnowledgePointResponse(BaseModel):
    id: int
    chapter_id: int
    title: str
    content: str | None = None
    difficulty: str
    prerequisites: list[int] | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
