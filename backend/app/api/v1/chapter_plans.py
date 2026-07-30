"""章节学习计划 API"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.course import Chapter
from app.services.student_state import StudentStateService
from app.services.personalization import PersonalizationService

router = APIRouter()


# ── Pydantic models ──


class ChapterTask(BaseModel):
    """单个学习任务"""
    task_id: str
    task_type: str
    title: str
    description: str = ""
    estimated_minutes: float
    resource_types: list[str]
    difficulty: str = "medium"
    personalization_reason: list[str] = Field(default_factory=list)


class ChapterPlanResponse(BaseModel):
    """章节学习计划响应"""
    chapter_id: int
    tasks: list[ChapterTask]
    estimated_total_minutes: float
    description: str


class TaskCompletionRequest(BaseModel):
    """完成任务请求"""
    status: str = "completed"
    correct_rate: float | None = None
    score: float | None = None


class TaskCompletionResponse(BaseModel):
    """完成任务响应"""
    success: bool
    chapter_id: int
    task_id: str
    status: str
    correct_rate: float | None = None
    score: float | None = None
    completion_rate: float
    average_correct_rate: float
    current_task_index: int
    total_tasks: int
    adjustment: dict | None = None


class ChapterProgressResponse(BaseModel):
    """章节进度摘要"""
    chapter_id: int
    completion_rate: float
    average_correct_rate: float
    estimated_remaining_minutes: float
    task_distribution: dict[str, int]
    recent_completions: list[dict]
    tasks: list[dict] = []


# ── Helpers ──


async def _get_chapter_or_404(chapter_id: int, db: AsyncSession) -> Chapter:
    """获取章节，不存在则抛出404"""
    result = await db.execute(
        select(Chapter)
        .where(Chapter.id == chapter_id)
        .options(selectinload(Chapter.knowledge_points))
    )
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return chapter


# ── Endpoints ──


@router.get("/{chapter_id}", response_model=ChapterPlanResponse)
async def get_chapter_plan(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取章节学习计划——确定性结构：每个知识点 → 学习+练习，然后章节检测+复习"""
    chapter = await _get_chapter_or_404(chapter_id, db)
    kps = sorted(chapter.knowledge_points, key=lambda kp: kp.sort_order)

    normalized_tasks: list[dict] = []

    # 每个知识点：学习 + 练习
    for i, kp in enumerate(kps):
        normalized_tasks.append({
            "task_id": f"ch{chapter_id}_learn_{kp.id}",
            "task_type": "learn",
            "title": f"学习：{kp.title}",
            "description": kp.content or f"学习本章节核心概念：{kp.title}",
            "estimated_minutes": 15,
            "resource_types": ["document", "mindmap", "reading"],
            "difficulty": kp.difficulty or "medium",
            "personalization_reason": [],
        })
        normalized_tasks.append({
            "task_id": f"ch{chapter_id}_practice_{kp.id}",
            "task_type": "practice",
            "title": f"练习：{kp.title}",
            "description": f"完成 {kp.title} 的针对性练习，巩固理解",
            "estimated_minutes": 10,
            "resource_types": ["exercise"],
            "difficulty": kp.difficulty or "medium",
            "personalization_reason": [],
        })

    # 章节总检测（计分）
    normalized_tasks.append({
        "task_id": f"ch{chapter_id}_assessment",
        "task_type": "assessment",
        "title": f"章节检测：{chapter.title}",
        "description": f"基于本章全部 {len(kps)} 个知识点的综合检测，计分",
        "estimated_minutes": 15,
        "resource_types": ["exercise"],
        "difficulty": "medium",
        "personalization_reason": [],
    })

    # 章节复习
    normalized_tasks.append({
        "task_id": f"ch{chapter_id}_review",
        "task_type": "review",
        "title": f"章节复习：{chapter.title}",
        "description": "回顾本章全部知识点，梳理知识框架，查漏补缺",
        "estimated_minutes": 10,
        "resource_types": ["document", "mindmap"],
        "difficulty": "medium",
        "personalization_reason": [],
    })

    total_minutes = sum(t["estimated_minutes"] for t in normalized_tasks)
    description = f"本章共 {len(kps)} 个知识点，{len(normalized_tasks)} 项任务，预计 {total_minutes} 分钟"

    # 初始化任务跟踪
    student_state = StudentStateService()
    await student_state.track_chapter_task_progress(
        user_id=current_user.id,
        course_id=chapter.course_id,
        chapter_id=chapter_id,
        tasks=normalized_tasks,
    )

    return ChapterPlanResponse(
        chapter_id=chapter_id,
        tasks=[ChapterTask(**t) for t in normalized_tasks],
        estimated_total_minutes=total_minutes,
        description=description,
    )


@router.post("/{chapter_id}/tasks/{task_id}/complete", response_model=TaskCompletionResponse)
async def complete_task(
    chapter_id: int,
    task_id: str,
    data: TaskCompletionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """完成任务"""
    chapter = await _get_chapter_or_404(chapter_id, db)
    course_id = chapter.course_id

    result = await StudentStateService().update_task_completion(
        user_id=current_user.id,
        course_id=course_id,
        chapter_id=chapter_id,
        task_id=task_id,
        status=data.status,
        correct_rate=data.correct_rate,
        score=data.score,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    adaptation = await PersonalizationService().replan_active_path(
        current_user.id,
        course_id,
        correct_rate=data.correct_rate,
    )
    if adaptation:
        result["path_adjustment"] = adaptation

    return TaskCompletionResponse(
        success=result.get("success", False),
        chapter_id=result.get("chapter_id", chapter_id),
        task_id=result.get("task_id", task_id),
        status=result.get("status", data.status),
        correct_rate=result.get("correct_rate"),
        score=result.get("score"),
        completion_rate=result.get("completion_rate", 0.0),
        average_correct_rate=result.get("average_correct_rate", 0.0),
        current_task_index=result.get("current_task_index", 0),
        total_tasks=result.get("total_tasks", 0),
        adjustment=result.get("adjustment"),
    )


@router.get("/{chapter_id}/progress", response_model=ChapterProgressResponse)
async def get_chapter_progress(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取章节进度摘要"""
    chapter = await _get_chapter_or_404(chapter_id, db)
    course_id = chapter.course_id

    summary = await StudentStateService().get_chapter_progress_summary(
        user_id=current_user.id,
        course_id=course_id,
        chapter_id=chapter_id,
    )

    if "error" in summary:
        raise HTTPException(status_code=400, detail=summary["error"])

    # 转换 task_type_breakdown 为 task_distribution
    task_breakdown = summary.get("task_type_breakdown", {})
    task_distribution = {
        ttype: (data["total"] if isinstance(data, dict) else 0)
        for ttype, data in task_breakdown.items()
    }

    return ChapterProgressResponse(
        chapter_id=summary.get("chapter_id", chapter_id),
        completion_rate=summary.get("completion_rate", 0.0),
        average_correct_rate=summary.get("average_correct_rate", 0.0),
        estimated_remaining_minutes=summary.get("estimated_remaining_minutes", 0.0),
        task_distribution=task_distribution,
        recent_completions=summary.get("recent_completions", []),
        tasks=summary.get("tasks", []),
    )