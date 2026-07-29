"""认证 API"""

from __future__ import annotations

import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
    get_current_user,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from app.schemas.user import ForgotPasswordRequest, ResetPasswordRequest, ForgotPasswordResponse
from app.core.config import settings
from app.services.redis_client import get_redis
from app.services.email_service import send_reset_code

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    # 检查用户名或邮箱是否已存在
    result = await db.execute(
        select(User).where(
            or_(User.username == data.username, User.email == data.email)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名或邮箱已存在",
        )

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=get_password_hash(data.password),
        display_name=data.display_name or data.username,
        is_admin=data.username.lower() in settings.admin_usernames,
    )
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)

    # 创建初始画像
    from app.models.student_profile import StudentProfile
    profile = StudentProfile(
        user_id=user.id,
        profile_data={
            "knowledge_base": {"level": "beginner", "subjects": []},
            "cognitive_style": {"preference": "visual", "description": ""},
            "learning_goals": {"short_term": "", "long_term": ""},
            "knowledge_gaps": [],
            "learning_pace": {"speed": "normal", "preferred_session_minutes": 30},
            "interest_direction": {"areas": []},
            "weak_points": [],
            "_meta": {"evidence": [], "last_analysis": {}},
        },
    )
    db.add(profile)
    await db.flush()
    await db.commit()

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(
        select(User).where(
            or_(User.username == data.username, User.email == data.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse.model_validate(current_user)

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """发送密码重置验证码"""
    message = "如果该邮箱已注册，验证码已发送至您的邮箱"

    # 查找用户（不暴露邮箱是否存在）
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        return ForgotPasswordResponse(message=message)

    # 生成 6 位验证码和重置 token
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    token = secrets.token_urlsafe(32)

    redis = get_redis()
    await redis.set(
        f"pwd_reset:{data.email}",
        '{"code":"' + code + '","token":"' + token + '"}',
        ex=900,
    )

    # 发送验证码邮件（或记录到日志）
    send_ok = send_reset_code(data.email, code)

    if settings.DEBUG and send_ok:
        return ForgotPasswordResponse(message=message, dev_code=code, dev_token=token)

    return ForgotPasswordResponse(message=message)


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """验证验证码并重置密码"""
    redis = get_redis()
    stored = await redis.get(f"pwd_reset:{data.email}")
    if not stored:
        raise HTTPException(status_code=400, detail="验证码已过期或未请求重置")

    import json
    payload = json.loads(stored)

    if payload.get("code") != data.code:
        raise HTTPException(status_code=400, detail="验证码错误")

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.hashed_password = get_password_hash(data.new_password)
    await db.flush()
    await db.commit()

    await redis.delete(f"pwd_reset:{data.email}")

    return {"message": "密码重置成功"}
