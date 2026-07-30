"""绔犺妭 API"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.course import Chapter, Course
from app.models.knowledge_point import KnowledgePoint
from app.schemas.course import ChapterCreate, ChapterResponse
from app.schemas.knowledge_point import KnowledgePointResponse

router = APIRouter()


@router.get("/course/{course_id}", response_model=list[ChapterResponse])
async def list_chapters(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the chapters in a course."""
    result = await db.execute(
        select(Chapter)
        .where(Chapter.course_id == course_id)
        .order_by(Chapter.sort_order)
        .options(selectinload(Chapter.knowledge_points))
    )
    chapters = result.scalars().all()
    return [ChapterResponse.model_validate(c) for c in chapters]


@router.get("/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get chapter details."""
    result = await db.execute(
        select(Chapter)
        .where(Chapter.id == chapter_id)
        .options(selectinload(Chapter.knowledge_points))
    )
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return ChapterResponse.model_validate(chapter)


@router.post("/", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED)
async def create_chapter(
    data: ChapterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """鍒涘缓绔犺妭"""
    # 楠岃瘉璇剧▼瀛樺湪
    course_result = await db.execute(select(Course).where(Course.id == data.course_id))
    if not course_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Course not found")

    chapter = Chapter(**data.model_dump())
    db.add(chapter)
    await db.flush()
    await db.commit()
    await db.refresh(chapter)
    return ChapterResponse.model_validate(chapter)


@router.put("/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    chapter_id: int,
    data: ChapterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """鏇存柊绔犺妭"""
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(chapter, key, value)
    await db.flush()
    await db.commit()
    await db.refresh(chapter)
    return ChapterResponse.model_validate(chapter)


@router.delete("/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chapter(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chapter."""
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    await db.delete(chapter)
    await db.commit()
