"""Deterministic personalization layer shared by the path and resource APIs."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.learning_resource import LearningResource
from app.models.study_path import StudyPath
from app.services.student_state import StudentStateService


RESOURCE_LABELS = {
    "document": "讲义",
    "video": "视频微课",
    "exercise": "针对练习",
    "code": "实操案例",
    "mindmap": "知识结构图",
    "reading": "拓展阅读",
}


class PersonalizationService:
    """Turn the existing learner snapshot into explainable recommendations."""

    @staticmethod
    def profile_reason(profile: dict[str, Any], node: dict[str, Any]) -> list[str]:
        preference = str(profile.get("cognitive_style", {}).get("preference", "")).strip()
        gaps = profile.get("knowledge_gaps", []) or profile.get("weak_points", []) or []
        reasons: list[str] = []
        if preference:
            reasons.append(f"匹配你的{preference}学习偏好")
        if gaps:
            reasons.append(f"优先巩固薄弱点：{str(gaps[0])}")
        if node.get("type") in {"review", "practice"}:
            reasons.append("根据当前进度安排巩固与检测")
        return reasons or ["按课程知识依赖与当前进度安排"]

    @staticmethod
    def preferred_types(profile: dict[str, Any], node: dict[str, Any]) -> list[str]:
        preference = str(profile.get("cognitive_style", {}).get("preference", "")).lower()
        ordered = ["document"]
        if any(word in preference for word in ("视觉", "visual", "听觉", "auditory")):
            ordered.extend(["video", "mindmap"])
        if any(word in preference for word in ("实践", "practical")):
            ordered.extend(["code", "exercise"])
        if any(word in preference for word in ("逻辑", "logical", "阅读", "reading")):
            ordered.extend(["exercise", "reading"])
        if node.get("type") in {"practice", "exam"}:
            ordered.insert(0, "exercise")
        if node.get("type") == "review":
            ordered.insert(0, "mindmap")
        return list(dict.fromkeys(ordered))

    async def recommend_current_task(self, user_id: int, path_id: int, node_id: str) -> dict[str, Any]:
        state = await StudentStateService().load(user_id)
        async with async_session_factory() as db:
            path = (
                await db.execute(select(StudyPath).where(StudyPath.id == path_id, StudyPath.user_id == user_id))
            ).scalar_one_or_none()
            if not path:
                raise LookupError("学习路径不存在")
            node = next((item for item in path.path_data.get("nodes", []) if item.get("id") == node_id), None)
            if not node:
                raise LookupError("学习节点不存在")
            query = select(LearningResource).where(
                LearningResource.course_id == path.course_id,
                LearningResource.user_id.in_([user_id, 1]),
            )
            if node.get("resource_ids"):
                query = query.where(LearningResource.id.in_(node["resource_ids"]))
            elif node.get("knowledge_point_id"):
                query = query.where(LearningResource.knowledge_point_id == node["knowledge_point_id"])
            else:
                # Chapter-level preview nodes must not accidentally surface a
                # later knowledge point's lecture as their current content.
                resources = []
                profile = state["profile"]["data"]
                reasons = self.profile_reason(profile, node)
                return {
                    "state_snapshot_id": state["snapshot_id"],
                    "node": node,
                    "planning_reasons": node.get("personalization_reason") or reasons,
                    "resources": [],
                }
            resources = (await db.execute(query)).scalars().all()

        profile = state["profile"]["data"]
        preferred = self.preferred_types(profile, node)
        resource_ids = node.get("resource_ids") or []
        ranked = sorted(
            resources,
            key=lambda item: (
                0 if item.id in resource_ids else 1,
                preferred.index(item.resource_type) if item.resource_type in preferred else len(preferred),
                -item.id,
            ),
        )
        reasons = self.profile_reason(profile, node)
        return {
            "state_snapshot_id": state["snapshot_id"],
            "node": node,
            "planning_reasons": node.get("personalization_reason") or reasons,
            "resources": [
                {
                    "resource": item,
                    "rank": index + 1,
                    "reason": f"{RESOURCE_LABELS.get(item.resource_type, item.resource_type)}：{reasons[0]}",
                }
                for index, item in enumerate(ranked)
            ],
        }

    async def replan_active_path(self, user_id: int, course_id: int, *, correct_rate: float | None = None) -> dict[str, Any] | None:
        """Adapt only pending nodes; completed learning evidence is never rewritten."""
        state = await StudentStateService().load(user_id, course_id)
        async with async_session_factory() as db:
            path = (
                await db.execute(select(StudyPath).where(
                    StudyPath.user_id == user_id, StudyPath.course_id == course_id, StudyPath.is_active == True,
                ))
            ).scalar_one_or_none()
            if not path:
                return None
            nodes = list(path.path_data.get("nodes", []))
            pending_index = next((i for i, node in enumerate(nodes) if node.get("status") != "completed"), len(nodes))
            summary = "已根据最新学习进度刷新后续任务。"
            if correct_rate is not None and correct_rate < 0.5 and pending_index < len(nodes):
                next_node = nodes[pending_index]
                review = {
                    "id": f"adaptive-review-{next_node.get('id')}",
                    "title": f"针对复习：{next_node.get('knowledge_point_title') or next_node.get('title')}",
                    "type": "review",
                    "status": "in_progress",
                    "estimated_minutes": 15,
                    "chapter_id": next_node.get("chapter_id"),
                    "knowledge_point_id": next_node.get("knowledge_point_id"),
                    "chapter_title": next_node.get("chapter_title"),
                    "knowledge_point_title": next_node.get("knowledge_point_title"),
                    "difficulty": "easy",
                    "recommended_resource_types": ["mindmap", "document", "exercise"],
                    "personalization_reason": ["最近练习正确率低于 50%，先回顾核心概念再继续。"],
                    "state_snapshot_id": state["snapshot_id"],
                    "resource_ids": next_node.get("resource_ids", []),
                }
                if not str(next_node.get("id", "")).startswith("adaptive-review-"):
                    nodes.insert(pending_index, review)
                summary = "检测到练习正确率偏低，已在下一步前插入针对性复习。"
            elif correct_rate is not None and correct_rate >= 0.7 and pending_index < len(nodes):
                nodes[pending_index] = {**nodes[pending_index], "difficulty": "hard", "personalization_reason": ["近期掌握良好，下一步提升为进阶任务。"]}
                summary = "近期掌握良好，已提高下一步任务的挑战度。"
            path.path_data = {
                **path.path_data,
                "nodes": nodes,
                "current_index": pending_index,
                "student_state_snapshot_id": state["snapshot_id"],
                "profile_version": state["profile"]["version"],
                "adjustment_summary": summary,
            }
            await db.commit()
        return {"summary": summary, "snapshot_id": state["snapshot_id"]}
