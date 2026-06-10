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
from app.schemas.student_profile import StudentProfileResponse

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
        from app.models.student_profile import StudentProfile as SP
        profile = SP(user_id=current_user.id, profile_data={})
        db.add(profile)
        await db.flush()
        await db.refresh(profile)

    return StudentProfileResponse.model_validate(profile)
