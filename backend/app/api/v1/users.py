"""用户 API"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.student_profile import StudentProfile
from app.schemas.user import UserResponse
from app.schemas.student_profile import StudentProfileResponse, ProfileFormRequest

router = APIRouter()


@router.get("/profile", response_model=StudentProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户画像"""
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = StudentProfile(user_id=current_user.id, profile_data={})
        db.add(profile)
        await db.flush()
        await db.commit()
        await db.refresh(profile)

    return StudentProfileResponse.model_validate(profile)


@router.put("/profile", response_model=StudentProfileResponse)
async def update_profile(
    data: ProfileFormRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新用户画像，所有字段可选，只合并非空值"""
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = StudentProfile(user_id=current_user.id, profile_data={})
        db.add(profile)

    # 合并子字段（只合并非空的值）
    profile_data = dict(profile.profile_data or {})

    if data.knowledge_base is not None:
        kb = profile_data.setdefault("knowledge_base", {})
        if data.knowledge_base.level is not None:
            kb["level"] = data.knowledge_base.level
        if data.knowledge_base.subjects is not None:
            kb["subjects"] = data.knowledge_base.subjects

    if data.cognitive_style is not None:
        cs = profile_data.setdefault("cognitive_style", {})
        if data.cognitive_style.preference is not None:
            cs["preference"] = data.cognitive_style.preference
        if data.cognitive_style.description is not None:
            cs["description"] = data.cognitive_style.description

    if data.learning_goals is not None:
        lg = profile_data.setdefault("learning_goals", {})
        if data.learning_goals.short_term is not None:
            lg["short_term"] = data.learning_goals.short_term
        if data.learning_goals.long_term is not None:
            lg["long_term"] = data.learning_goals.long_term

    if data.learning_pace is not None:
        lp = profile_data.setdefault("learning_pace", {})
        if data.learning_pace.speed is not None:
            lp["speed"] = data.learning_pace.speed
        if data.learning_pace.preferred_session_minutes is not None:
            lp["preferred_session_minutes"] = data.learning_pace.preferred_session_minutes

    if data.interest_direction is not None and data.interest_direction.areas is not None:
        profile_data.setdefault("interest_direction", {})["areas"] = data.interest_direction.areas

    if data.resource_preferences is not None and data.resource_preferences.types is not None:
        profile_data.setdefault("resource_preferences", {})["types"] = data.resource_preferences.types

    if data.knowledge_gaps is not None:
        profile_data["knowledge_gaps"] = data.knowledge_gaps

    if data.weak_points is not None:
        profile_data["weak_points"] = data.weak_points

    # 标记 onboarding 完成
    meta = profile_data.setdefault("_meta", {})
    meta["onboarding_completed"] = True
    profile_data["_meta"] = meta

    profile.profile_data = profile_data
    profile.version += 1

    await db.flush()
    await db.commit()
    await db.refresh(profile)

    return StudentProfileResponse.model_validate(profile)
