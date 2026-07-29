"""学生画像 Pydantic Schemas"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


# --- 内部子结构 ---

class KnowledgeBaseData(BaseModel):
    level: str | None = Field(None, description="水平: beginner/intermediate/advanced")
    subjects: list[str] | None = Field(None, description="熟悉领域列表")


class CognitiveStyleData(BaseModel):
    preference: str | None = Field(None, description="偏好: visual/auditory/reading/kinesthetic/mixed")
    description: str | None = Field(None, description="认知风格描述")


class LearningGoalsData(BaseModel):
    short_term: str | None = Field(None, description="短期目标")
    long_term: str | None = Field(None, description="长期目标")


class LearningPaceData(BaseModel):
    speed: str | None = Field(None, description="学习速度: slow/normal/fast")
    preferred_session_minutes: int | None = Field(None, ge=5, le=240, description="单次专注时长(分钟)")


class InterestDirectionData(BaseModel):
    areas: list[str] | None = Field(None, description="兴趣方向列表")


# --- 新增: 画像初始化请求（Onboarding） ---

class ProfileFormRequest(BaseModel):
    """前端表单提交的画像更新请求，所有字段均可选"""
    knowledge_base: KnowledgeBaseData | None = None
    cognitive_style: CognitiveStyleData | None = None
    learning_goals: LearningGoalsData | None = None
    learning_pace: LearningPaceData | None = None
    interest_direction: InterestDirectionData | None = None
    knowledge_gaps: list[str] | None = None
    weak_points: list[str] | None = None


# --- 响应 ---

class StudentProfileResponse(BaseModel):
    id: int
    user_id: int
    profile_data: dict
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdateRequest(BaseModel):
    """仅 Agent 内部调用，用户不可手动编辑"""
    profile_data: dict
    version: int = Field(..., description="乐观锁版本号")
