"""评估报告 Pydantic Schemas"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class EvaluationResponse(BaseModel):
    id: int
    user_id: int
    course_id: int | None = None
    scores: dict
    suggestions: list[str] | None = None
    strategy_signals: dict | None = None
    report_data: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
