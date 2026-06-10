"""学生画像 Pydantic Schemas"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class StudentProfileResponse(BaseModel):
    id: int
    user_id: int
    profile_data: dict
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdateRequest(BaseModel):
    """仅限 Agent 内部调用，用户不可手动编辑"""
    profile_data: dict
    version: int = Field(..., description="乐观锁版本号")
