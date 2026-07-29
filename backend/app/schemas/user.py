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
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., description="注册时使用的邮箱")


class ResetPasswordRequest(BaseModel):
    email: str = Field(..., description="注册时使用的邮箱")
    code: str = Field(..., min_length=6, max_length=6, description="验证码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")


class ForgotPasswordResponse(BaseModel):
    message: str
    dev_code: str | None = None
    dev_token: str | None = None
