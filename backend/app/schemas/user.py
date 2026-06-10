"""用户认证 Pydantic Schemas"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    display_name: str | None = Field(None, max_length=100, description="显示名称")


class UserLogin(BaseModel):
    username: str = Field(..., description="用户名/邮箱")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    display_name: str | None
    avatar_url: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
