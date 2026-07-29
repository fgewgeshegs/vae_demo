"""Pydantic schemas for explicit learning tasks."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


TaskType = Literal[
    "generate_study_path",
    "update_profile",
    "generate_learning_resource",
    "generate_evaluation",
]


class LearningTaskCreate(BaseModel):
    task_type: TaskType
    course_id: int | None = None
    input: dict[str, Any] = Field(default_factory=dict)


class LearningTaskStep(BaseModel):
    name: str
    status: str
    label: str | None = None
    error: str | None = None


class LearningTaskResponse(BaseModel):
    id: int
    task_type: str
    user_id: int
    course_id: int | None
    status: str
    input: dict[str, Any]
    steps: list[LearningTaskStep | dict[str, Any]]
    result: dict[str, Any]
    error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
