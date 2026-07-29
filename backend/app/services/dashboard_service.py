"""Read-only aggregation for the action-first learning dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.evaluation import Evaluation
from app.models.learning_behavior import LearningBehavior
from app.models.qa_record import QARecord
from app.models.student_profile import StudentProfile
from app.models.study_path import StudyPath


NODE_TYPES = {"preview", "learn", "practice", "review", "exam"}


def select_current_node(nodes: list[dict[str, Any]], current_index: Any) -> tuple[int | None, dict[str, Any] | None]:
    """Return the declared current node, with safe state-based fallbacks."""
    if isinstance(current_index, int) and 0 <= current_index < len(nodes):
        candidate = nodes[current_index]
        if isinstance(candidate, dict) and candidate.get("status") != "completed":
            return current_index, candidate
    for index, node in enumerate(nodes):
        if isinstance(node, dict) and node.get("status") == "in_progress":
            return index, node
    for index, node in enumerate(nodes):
        if isinstance(node, dict) and node.get("status") == "pending":
            return index, node
    return None, None


def build_recommendation(profile: StudentProfile | None, evaluation: Evaluation | None, node: dict[str, Any]) -> dict[str, Any] | None:
    """Produce at most three user-readable reasons backed by stored evidence."""
    reasons: list[dict[str, str]] = []
    profile_data = profile.profile_data if profile else {}
    title = str(node.get("knowledge_point_title") or node.get("title") or "当前知识点")
    evidence_terms = " ".join([title, str(node.get("learning_content") or ""), str(node.get("chapter_title") or "")]).lower()
    for weak_point in list(profile_data.get("knowledge_gaps") or []) + list(profile_data.get("weak_points") or []):
        if str(weak_point).lower() in evidence_terms:
            reasons.append({"kind": "knowledge_gap", "label": "待巩固知识点", "evidence": f"画像记录显示你在“{weak_point}”上仍需巩固。"})
            break
    if evaluation and evaluation.strategy_signals:
        for key, value in evaluation.strategy_signals.items():
            if value:
                readable = str(value) if isinstance(value, str) else str(key).replace("_", " ")
                reasons.append({"kind": "evaluation_signal", "label": "最近评估建议", "evidence": f"最近一次学习诊断建议：{readable}。"})
                break
    pace = profile_data.get("learning_pace") or {}
    minutes = pace.get("preferred_session_minutes")
    if isinstance(minutes, int) and minutes > 0:
        reasons.append({"kind": "learning_pace", "label": "学习节奏", "evidence": f"当前任务约 {node.get('estimated_minutes') or 0} 分钟，与你设定的 {minutes} 分钟学习节奏相匹配。"})
    if not reasons:
        return None
    return {"headline": "系统为何建议你现在完成这一步", "reasons": reasons[:3], "profile_version": profile.version if profile else None}


def build_feedback(evaluation: Evaluation | None, total_nodes: int) -> dict[str, str | None] | None:
    if evaluation and evaluation.strategy_signals:
        for key, value in evaluation.strategy_signals.items():
            if value:
                readable = str(value) if isinstance(value, str) else str(key).replace("_", " ")
                return {"message": "完成本次任务后，系统会结合新的学习记录更新诊断，并据此调整下一步建议。", "source": "evaluation", "strategy_signal": readable}
    if total_nodes:
        return {"message": "完成本次任务后，系统会记录学习进度，并推进到下一步学习建议。", "source": "path_progress", "strategy_signal": None}
    return None


def build_today_tasks(nodes: list[dict[str, Any]], start_index: int | None) -> list[dict[str, Any]]:
    """Expose the next small set of actionable path nodes for the dashboard."""
    start = start_index if start_index is not None else 0
    tasks: list[dict[str, Any]] = []
    for node in nodes[start:]:
        if node.get("status") == "completed":
            continue
        tasks.append({
            "id": str(node.get("id") or len(tasks)),
            "title": str(node.get("title") or node.get("knowledge_point_title") or "学习任务"),
            "node_type": str(node.get("type") or "learn"),
            "estimated_minutes": int(node.get("estimated_minutes") or 0),
            "status": str(node.get("status") or "pending"),
        })
        if len(tasks) == 5:
            break
    return tasks


def build_profile_summary(profile: StudentProfile | None) -> dict[str, Any] | None:
    if not profile:
        return None
    data = profile.profile_data or {}
    return {
        "version": profile.version,
        "profile_data": data,
        "knowledge_gaps": list(data.get("knowledge_gaps") or [])[:3],
        "weak_points": list(data.get("weak_points") or [])[:3],
    }


async def build_learning_activity(db: AsyncSession, user_id: int) -> dict[str, Any]:
    """Aggregate persisted behaviors into chart-ready hourly and weekly data."""
    now = datetime.now().astimezone()
    start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    behaviors = (
        await db.execute(
            select(LearningBehavior).where(
                LearningBehavior.user_id == user_id,
                LearningBehavior.created_at >= start,
                LearningBehavior.duration_seconds > 0,
            )
        )
    ).scalars().all()
    daily = {str((start + timedelta(days=index)).date()): {"minutes": 0, "tasks": 0} for index in range(7)}
    hourly = [{"hour": hour, "minutes": 0, "tasks": 0} for hour in range(24)]
    for behavior in behaviors:
        timestamp = behavior.created_at.astimezone(now.tzinfo) if behavior.created_at.tzinfo else behavior.created_at
        key = str(timestamp.date())
        minutes = round(behavior.duration_seconds / 60)
        tasks = int((behavior.behavior_metadata or {}).get("completed_tasks") or 0)
        if key in daily:
            daily[key]["minutes"] += minutes
            daily[key]["tasks"] += tasks
        hourly[timestamp.hour]["minutes"] += minutes
        hourly[timestamp.hour]["tasks"] += tasks
    return {
        "daily": [{"date": key, **value} for key, value in daily.items()],
        "hourly": hourly,
        "week_minutes": sum(item["minutes"] for item in daily.values()),
        "active_days": sum(1 for item in daily.values() if item["minutes"] > 0),
    }


class DashboardService:
    @staticmethod
    async def overview(db: AsyncSession, user_id: int) -> dict[str, Any]:
        path = (await db.execute(select(StudyPath).where(StudyPath.user_id == user_id, StudyPath.is_active.is_(True)).order_by(StudyPath.updated_at.desc()).limit(1))).scalar_one_or_none()
        profile = (await db.execute(select(StudentProfile).where(StudentProfile.user_id == user_id))).scalar_one_or_none()
        activity = await build_learning_activity(db, user_id)
        if not path:
            return {**DashboardService._empty_overview("no_path"), "learning_activity": activity}
        course = await db.get(Course, path.course_id)
        evaluation = (await db.execute(select(Evaluation).where(Evaluation.user_id == user_id, or_(Evaluation.course_id == path.course_id, Evaluation.course_id.is_(None))).order_by(Evaluation.created_at.desc()).limit(1))).scalar_one_or_none()
        recent_qa = (await db.execute(select(QARecord).where(QARecord.user_id == user_id).order_by(QARecord.created_at.desc()).limit(50))).scalars().all()
        path_data = path.path_data or {}
        nodes = [node for node in path_data.get("nodes", []) if isinstance(node, dict)]
        current_index, node = select_current_node(nodes, path_data.get("current_index"))
        completed_nodes = sum(node_item.get("status") == "completed" for node_item in nodes)
        dates = [path.updated_at, profile.updated_at if profile else None, evaluation.created_at if evaluation else None]
        dates.extend(record.created_at for record in recent_qa[:1])
        last_activity = max((item for item in dates if item is not None), default=None)
        state = {"completed_nodes": completed_nodes, "total_nodes": len(nodes), "recent_qa_count": len(recent_qa), "last_activity_at": last_activity.isoformat() if last_activity else None}
        if not node:
            return {**DashboardService._empty_overview("partial"), "learning_state": state, "feedback": build_feedback(evaluation, len(nodes)), "profile_summary": build_profile_summary(profile), "today_tasks": [], "learning_activity": activity}
        next_node = next((item for item in nodes[(current_index or 0) + 1:] if item.get("status") != "completed"), None)
        node_type = str(node.get("type") or "learn")
        current_task = {
            "path_id": path.id, "course_id": path.course_id,
            "course_title": str(path_data.get("course_title") or (course.title if course else "当前课程")),
            "node_id": str(node.get("id") or current_index or "current"),
            "title": str(node.get("title") or node.get("knowledge_point_title") or "当前学习任务"),
            "node_type": node_type if node_type in NODE_TYPES else "learn", "difficulty": node.get("difficulty"),
            "estimated_minutes": int(node.get("estimated_minutes") or 0),
            "progress_percent": round(max(0.0, min(path.progress, 1.0)) * 100),
            "resource_ids": list(node.get("resource_ids") or []),
            "primary_action": {"label": "开始当前任务", "target": "/path"},
            "next_step": str(next_node.get("title")) if next_node else "完成本路径复盘",
        }
        return {"status": "ready" if profile and evaluation else "partial", "generated_at": datetime.now().astimezone().isoformat(), "current_task": current_task, "recommendation": build_recommendation(profile, evaluation, node), "learning_state": state, "feedback": build_feedback(evaluation, len(nodes)), "profile_summary": build_profile_summary(profile), "today_tasks": build_today_tasks(nodes, current_index), "learning_activity": activity}

    @staticmethod
    def _empty_overview(status: str) -> dict[str, Any]:
        return {"status": status, "generated_at": datetime.now().astimezone().isoformat(), "current_task": None, "recommendation": None, "learning_state": {"completed_nodes": 0, "total_nodes": 0, "recent_qa_count": 0, "last_activity_at": None}, "feedback": None, "profile_summary": None, "today_tasks": [], "learning_activity": {"daily": [], "hourly": [], "week_minutes": 0, "active_days": 0}}
