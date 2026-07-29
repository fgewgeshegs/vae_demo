"""章节学习计划 API"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.course import Chapter
from app.services.student_state import StudentStateService
from app.agents.path_agent import PathAgent

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


def _format_evaluation_context(evaluation: dict) -> str | None:
    """将评估结果格式化为上下文字符串"""
    if "error" in evaluation:
        return None
    suggestions = evaluation.get("suggestions", [])
    if suggestions:
        return "评估建议：" + "；".join(suggestions)
    return None


# ── Endpoints ──


@router.get("/{chapter_id}", response_model=ChapterPlanResponse)
async def get_chapter_plan(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取章节学习计划"""
    chapter = await _get_chapter_or_404(chapter_id, db)
    course_id = chapter.course_id

    # 获取学生画像
    student_state = StudentStateService()
    profile = await student_state.load(
        user_id=current_user.id,
        course_id=course_id,
    )

    # 获取评估上下文
    evaluation = await student_state.evaluate_chapter_performance(
        user_id=current_user.id,
        course_id=course_id,
        chapter_id=chapter_id,
    )
    evaluation_context = _format_evaluation_context(evaluation)

    # 准备章节信息
    chapter_info = {
        "title": chapter.title,
        "knowledge_points": [
            {
                "title": kp.title,
                "difficulty": kp.difficulty or "medium",
            }
            for kp in chapter.knowledge_points
        ],
    }

    # 生成学习计划
    path_agent = PathAgent()
    plan = await path_agent.generate_chapter_learning_plan(
        chapter_info=chapter_info,
        profile=profile,
        evaluation_context=evaluation_context,
    )

    # 标准化任务数据并分配 task_id
    tasks = plan.get("tasks", [])
    normalized_tasks: list[dict] = []
    for i, task in enumerate(tasks):
        normalized_tasks.append({
            "task_id": f"ch{chapter_id}_task_{i + 1}",
            "task_type": task.get("task_type") or task.get("type", "learn"),
            "title": task.get("title", ""),
            "description": task.get("description", ""),
            "estimated_minutes": task.get("estimated_minutes", 0),
            "resource_types": task.get("resource_types", ["document"]),
            "difficulty": task.get("difficulty", "medium"),
        })

    # 初始化任务跟踪
    if normalized_tasks:
        await student_state.track_chapter_task_progress(
            user_id=current_user.id,
            course_id=course_id,
            chapter_id=chapter_id,
            tasks=normalized_tasks,
        )

    return ChapterPlanResponse(
        chapter_id=chapter_id,
        tasks=[ChapterTask(**t) for t in normalized_tasks],
        estimated_total_minutes=plan.get("estimated_total_minutes", 0),
        description=plan.get("description", ""),
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
