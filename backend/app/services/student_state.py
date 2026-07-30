"""Unified read model for learner state shared by agents."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.course import Chapter, Course
from app.models.evaluation import Evaluation
from app.models.knowledge_point import KnowledgePoint
from app.models.learning_behavior import LearningBehavior
from app.models.learning_resource import LearningResource
from app.models.qa_record import QARecord
from app.models.student_profile import StudentProfile
from app.models.study_path import StudyPath


DEFAULT_PROFILE_DATA = {
    "knowledge_base": {},
    "cognitive_style": {},
    "learning_goals": {},
    "knowledge_gaps": [],
    "learning_pace": {},
    "interest_direction": {},
    "weak_points": [],
    "learning_habits": {},
    "motivation_factors": {},
}


class StudentStateService:
    """Build consistent student-state snapshots for coordinators and agents."""

    async def load(
        self,
        user_id: int,
        course_id: int | None = None,
        *,
        include_recent: bool = True,
    ) -> dict[str, Any]:
        async with async_session_factory() as db:
            profile = (
                await db.execute(
                    select(StudentProfile).where(StudentProfile.user_id == user_id)
                )
            ).scalar_one_or_none()
            profile_data = dict(profile.profile_data) if profile else dict(DEFAULT_PROFILE_DATA)

            course_context = await self._load_course_context(db, course_id)
            active_paths = await self._load_active_paths(db, user_id, course_id)
            latest_evaluation = await self._load_latest_evaluation(db, user_id, course_id)

            recent_qa: list[dict[str, Any]] = []
            generated_resources: list[dict[str, Any]] = []
            if include_recent:
                recent_qa = await self._load_recent_qa(db, user_id, course_id)
                generated_resources = await self._load_recent_resources(db, user_id, course_id)

        return {
            "snapshot_id": self._snapshot_id(user_id, course_id),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "course_id": course_id,
            "profile": {
                "id": profile.id if profile else None,
                "version": profile.version if profile else 0,
                "data": profile_data,
                "created_at": profile.created_at.isoformat() if profile and profile.created_at else None,
                "updated_at": profile.updated_at.isoformat() if profile and profile.updated_at else None,
            },
            "recent_qa": recent_qa,
            "active_paths": active_paths,
            "generated_resources": generated_resources,
            "latest_evaluation": latest_evaluation,
            "course_context": course_context,
            "source_counts": {
                "recent_qa": len(recent_qa),
                "active_paths": len(active_paths),
                "generated_resources": len(generated_resources),
                "knowledge_points": len(course_context.get("knowledge_points", [])),
            },
        }

    async def load_learner_context(self, user_id: int, course_id: int | None = None) -> dict[str, Any]:
        state = await self.load(user_id, course_id, include_recent=False)
        return {
            "type": "learner_context",
            "snapshot_id": state["snapshot_id"],
            "profile": state["profile"]["data"],
            "profile_version": state["profile"]["version"],
            "active_paths": state["active_paths"],
            "latest_evaluation": state["latest_evaluation"],
        }

    async def load_course_context(self, course_id: int | None = None) -> dict[str, Any]:
        async with async_session_factory() as db:
            return await self._load_course_context(db, course_id)

    async def profile_summary(self, user_id: int, course_id: int | None = None) -> str:
        state = await self.load(user_id, course_id, include_recent=False)
        profile = state["profile"]["data"]
        if not profile:
            return "No learner profile yet."
        goals = profile.get("learning_goals", {})
        interests = profile.get("interest_direction", {})
        habits = profile.get("learning_habits", {})
        motivation = profile.get("motivation_factors", {})
        return "\n".join(
            [
                f"knowledge_level: {profile.get('knowledge_base', {}).get('level', 'unknown')}",
                f"cognitive_preference: {profile.get('cognitive_style', {}).get('preference', 'unknown')}",
                f"short_term_goal: {goals.get('short_term', 'unset')}",
                f"interests: {', '.join(interests.get('areas', []) or []) or 'unknown'}",
                f"knowledge_gaps: {', '.join(profile.get('knowledge_gaps', []) or []) or 'unknown'}",
                f"weak_points: {', '.join(profile.get('weak_points', []) or []) or 'unknown'}",
                f"preferred_time: {habits.get('preferred_time', 'unknown')}",
                f"review_frequency: {habits.get('review_frequency', 'unknown')}",
                f"motivation_intrinsic: {', '.join(motivation.get('intrinsic', []) or []) or 'unknown'}",
            ]
        )

    async def collect_learning_data(self, user_id: int, course_id: int | None = None) -> dict[str, Any]:
        since = datetime.now(timezone.utc) - timedelta(days=settings.ANALYTICS_LOOKBACK_DAYS)
        async with async_session_factory() as db:
            behavior_filters = (
                LearningBehavior.user_id == user_id,
                LearningBehavior.created_at >= since,
            )
            behavior_count, total_duration, active_days = (
                await db.execute(
                    select(
                        func.count(LearningBehavior.id),
                        func.coalesce(func.sum(LearningBehavior.duration_seconds), 0),
                        func.count(func.distinct(func.date(LearningBehavior.created_at))),
                    ).where(*behavior_filters)
                )
            ).one()
            action_type_counts = dict(
                (
                    await db.execute(
                        select(LearningBehavior.action_type, func.count(LearningBehavior.id))
                        .where(*behavior_filters)
                        .group_by(LearningBehavior.action_type)
                    )
                ).all()
            )

            qa_query = select(func.count(QARecord.id), func.count(QARecord.answer)).where(
                QARecord.user_id == user_id,
                QARecord.created_at >= since,
            )
            if course_id:
                qa_query = qa_query.where(QARecord.course_id == course_id)
            qa_count, answered_count = (await db.execute(qa_query)).one()

            active_paths = await self._load_active_paths(db, user_id, course_id)

            resource_query = select(func.count(LearningResource.id)).where(
                LearningResource.user_id == user_id
            )
            if course_id:
                resource_query = resource_query.where(LearningResource.course_id == course_id)
            resource_count = (await db.execute(resource_query)).scalar() or 0

            recent_evals = (
                await db.execute(
                    select(Evaluation)
                    .where(Evaluation.user_id == user_id)
                    .order_by(Evaluation.created_at.desc())
                    .limit(5)
                )
            ).scalars().all()

            profile = (
                await db.execute(
                    select(StudentProfile).where(StudentProfile.user_id == user_id)
                )
            ).scalar_one_or_none()
            profile_data = profile.profile_data if profile else {}

        score_trends = [
            {
                "date": ev.created_at.isoformat() if ev.created_at else "",
                "scores": ev.scores,
            }
            for ev in reversed(recent_evals)
        ]
        return {
            "is_empty": behavior_count == 0 and qa_count == 0 and resource_count == 0,
            "behavior": {
                "total_count": behavior_count,
                "action_types": action_type_counts,
                "total_duration_minutes": round(total_duration / 60, 1),
                "active_days": active_days,
            },
            "qa": {
                "total_count": qa_count,
                "answered_count": answered_count,
                "answer_rate": round(answered_count / qa_count * 100, 1) if qa_count > 0 else 0,
            },
            "progress": {
                "active_paths": len(active_paths),
                "path_details": [
                    {
                        "path_id": path["id"],
                        "progress": path["progress"],
                        "nodes_count": len(path.get("nodes", [])),
                        "current_index": path.get("current_index", 0),
                    }
                    for path in active_paths
                ],
            },
            "resources": {"total_count": resource_count},
            "score_trends": score_trends,
            "profile_summary": {
                "level": profile_data.get("knowledge_base", {}).get("level", "unknown"),
                "gaps": profile_data.get("knowledge_gaps", []),
                "weak_points": profile_data.get("weak_points", []),
                "goals": profile_data.get("learning_goals", {}),
                "habits": profile_data.get("learning_habits", {}),
                "motivation": profile_data.get("motivation_factors", {}),
            },
        }

    async def _load_course_context(self, db, course_id: int | None) -> dict[str, Any]:
        course_query = select(Course).where(Course.is_active == True)
        if course_id:
            course_query = course_query.where(Course.id == course_id)
        # The textbook-synchronised course is marked as the seed course. Prefer it
        # over legacy demo courses while still allowing an explicit course_id.
        courses = (
            await db.execute(course_query.order_by(Course.seed_course.desc(), Course.id))
        ).scalars().all()

        target_course = courses[0] if courses else None
        chapters: list[dict[str, Any]] = []
        knowledge_points: list[dict[str, Any]] = []
        if target_course:
            chapter_rows = (
                await db.execute(
                    select(Chapter)
                    .where(Chapter.course_id == target_course.id)
                    .order_by(Chapter.sort_order)
                )
            ).scalars().all()
            for chapter in chapter_rows:
                chapter_data = self._chapter_dict(chapter)
                kp_rows = (
                    await db.execute(
                        select(KnowledgePoint)
                        .where(KnowledgePoint.chapter_id == chapter.id)
                        .order_by(KnowledgePoint.sort_order)
                    )
                ).scalars().all()
                chapter_data["knowledge_points"] = [self._knowledge_point_dict(kp) for kp in kp_rows]
                chapters.append(chapter_data)
                knowledge_points.extend(chapter_data["knowledge_points"])

        return {
            "course": self._course_dict(target_course) if target_course else None,
            "available_courses": [self._course_dict(course) for course in courses],
            "chapters": chapters,
            "knowledge_points": knowledge_points,
        }

    async def _load_active_paths(self, db, user_id: int, course_id: int | None) -> list[dict[str, Any]]:
        query = select(StudyPath).where(
            StudyPath.user_id == user_id,
            StudyPath.is_active == True,
        )
        if course_id:
            query = query.where(StudyPath.course_id == course_id)
        paths = (
            await db.execute(query.order_by(StudyPath.updated_at.desc()).limit(3))
        ).scalars().all()
        items = []
        for path in paths:
            nodes = path.path_data.get("nodes", [])
            current_index = path.path_data.get("current_index", 0)
            items.append(
                {
                    "id": path.id,
                    "course_id": path.course_id,
                    "progress": path.progress,
                    "current_index": current_index,
                    "nodes": nodes,
                    "current_node": (
                        nodes[current_index]
                        if nodes and current_index < len(nodes)
                        else None
                    ),
                    "updated_at": path.updated_at.isoformat() if path.updated_at else None,
                }
            )
        return items

    async def _load_latest_evaluation(self, db, user_id: int, course_id: int | None) -> dict[str, Any] | None:
        query = select(Evaluation).where(Evaluation.user_id == user_id)
        if course_id:
            query = query.where(Evaluation.course_id == course_id)
        evaluation = (
            await db.execute(query.order_by(Evaluation.created_at.desc()).limit(1))
        ).scalar_one_or_none()
        if not evaluation:
            return None
        return {
            "id": evaluation.id,
            "course_id": evaluation.course_id,
            "scores": evaluation.scores,
            "suggestions": evaluation.suggestions or [],
            "strategy_signals": evaluation.strategy_signals or {},
            "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
        }

    async def _load_recent_qa(self, db, user_id: int, course_id: int | None) -> list[dict[str, Any]]:
        query = select(QARecord).where(QARecord.user_id == user_id)
        if course_id:
            query = query.where(QARecord.course_id == course_id)
        records = (
            await db.execute(query.order_by(QARecord.created_at.desc()).limit(10))
        ).scalars().all()
        return [
            {
                "id": record.id,
                "course_id": record.course_id,
                "question": record.question,
                "answer": record.answer,
                "metadata": record.qa_metadata or {},
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
            for record in records
        ]

    async def _load_recent_resources(self, db, user_id: int, course_id: int | None) -> list[dict[str, Any]]:
        query = select(LearningResource).where(LearningResource.user_id == user_id)
        if course_id:
            query = query.where(LearningResource.course_id == course_id)
        resources = (
            await db.execute(query.order_by(LearningResource.created_at.desc()).limit(20))
        ).scalars().all()
        return [
            {
                "id": resource.id,
                "course_id": resource.course_id,
                "chapter_id": resource.chapter_id,
                "knowledge_point_id": resource.knowledge_point_id,
                "resource_type": resource.resource_type,
                "title": resource.title,
                "metadata": resource.resource_metadata or {},
                "is_generated": resource.is_generated,
                "created_at": resource.created_at.isoformat() if resource.created_at else None,
            }
            for resource in resources
        ]

    @staticmethod
    def _snapshot_id(user_id: int, course_id: int | None) -> str:
        now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"user-{user_id}-course-{course_id or 'all'}-{now}"

    async def track_chapter_progress(
        self,
        user_id: int,
        course_id: int,
        chapter_id: int,
        node_id: str,
        status: str,
        completion_time: int | None = None,
    ) -> dict[str, Any]:
        """跟踪章节学习进度"""
        try:
            # 1. 获取当前学习路径
            async with async_session_factory() as db:
                active_paths = (
                    await db.execute(
                        select(StudyPath).where(
                            StudyPath.user_id == user_id,
                            StudyPath.course_id == course_id,
                            StudyPath.is_active == True,
                        )
                    )
                ).scalars().all()
                
                if not active_paths:
                    return {"error": "没有找到活跃的学习路径"}
                
                # 2. 更新节点状态
                for path in active_paths:
                    nodes = path.path_data.get("nodes", [])
                    updated = False
                    
                    for i, node in enumerate(nodes):
                        if node.get("id") == node_id:
                            nodes[i]["status"] = status
                            if status == "completed":
                                nodes[i]["completed_at"] = datetime.now(timezone.utc).isoformat()
                                if completion_time:
                                    nodes[i]["completion_time_seconds"] = completion_time
                            updated = True
                            break
                    
                    if updated:
                        # 计算进度
                        completed_count = sum(1 for node in nodes if node.get("status") == "completed")
                        progress = completed_count / len(nodes) if nodes else 0
                        
                        # 更新路径
                        path.path_data["nodes"] = nodes
                        path.progress = progress
                        await db.commit()
                        
                        return {
                            "success": True,
                            "path_id": path.id,
                            "node_id": node_id,
                            "status": status,
                            "progress": progress,
                            "completed_count": completed_count,
                            "total_nodes": len(nodes),
                        }
                
                return {"error": f"未找到节点 {node_id}"}
                
        except Exception as e:
            logger.error(f"章节进度跟踪失败: {e}")
            return {"error": str(e)}

    async def collect_chapter_learning_data(
        self,
        user_id: int,
        course_id: int,
        chapter_id: int,
    ) -> dict[str, Any]:
        """收集章节学习数据"""
        try:
            # 1. 获取章节信息
            async with async_session_factory() as db:
                chapter = (
                    await db.execute(
                        select(Chapter).where(Chapter.id == chapter_id)
                    )
                ).scalar_one_or_none()
                
                if not chapter:
                    return {"error": "章节不存在"}
                
                # 2. 获取章节知识点
                knowledge_points = (
                    await db.execute(
                        select(KnowledgePoint).where(KnowledgePoint.chapter_id == chapter_id)
                        .order_by(KnowledgePoint.sort_order)
                    )
                ).scalars().all()
                
                # 3. 获取章节相关资源
                resources = (
                    await db.execute(
                        select(LearningResource).where(
                            LearningResource.user_id == user_id,
                            LearningResource.course_id == course_id,
                            LearningResource.chapter_id == chapter_id,
                        )
                    )
                ).scalars().all()
                
                # 4. 获取章节相关学习行为
                since = datetime.now(timezone.utc) - timedelta(days=30)
                behaviors = (
                    await db.execute(
                        select(LearningBehavior).where(
                            LearningBehavior.user_id == user_id,
                            LearningBehavior.created_at >= since,
                        )
                    )
                ).scalars().all()
                
                # 5. 获取章节相关问答记录
                qa_records = (
                    await db.execute(
                        select(QARecord).where(
                            QARecord.user_id == user_id,
                            QARecord.course_id == course_id,
                        )
                    )
                ).scalars().all()
                
                # 6. 获取最近评估
                recent_eval = (
                    await db.execute(
                        select(Evaluation).where(
                            Evaluation.user_id == user_id,
                            Evaluation.course_id == course_id,
                        ).order_by(Evaluation.created_at.desc()).limit(1)
                    )
                ).scalar_one_or_none()
            
            # 7. 分析学习数据
            chapter_data = {
                "chapter_id": chapter_id,
                "chapter_title": chapter.title,
                "knowledge_points_count": len(knowledge_points),
                "resources_count": len(resources),
                "resource_types": {},
                "learning_time_minutes": 0,
                "qa_count": len(qa_records),
                "recent_scores": [],
            }
            
            # 统计资源类型
            for resource in resources:
                resource_type = resource.resource_type
                chapter_data["resource_types"][resource_type] = chapter_data["resource_types"].get(resource_type, 0) + 1
            
            # 统计学习时间
            for behavior in behaviors:
                chapter_data["learning_time_minutes"] += behavior.duration_seconds / 60
            
            # 获取评估分数
            if recent_eval and recent_eval.scores:
                chapter_data["recent_scores"] = [recent_eval.scores]
            
            return chapter_data
            
        except Exception as e:
            logger.error(f"章节学习数据收集失败: {e}")
            return {"error": str(e)}

    async def evaluate_chapter_performance(
        self,
        user_id: int,
        course_id: int,
        chapter_id: int,
    ) -> dict[str, Any]:
        """评估章节学习表现"""
        try:
            # 1. 收集章节学习数据
            chapter_data = await self.collect_chapter_learning_data(user_id, course_id, chapter_id)
            
            if "error" in chapter_data:
                return chapter_data
            
            # 2. 计算评估指标
            evaluation = {
                "chapter_id": chapter_id,
                "chapter_title": chapter_data.get("chapter_title", ""),
                "metrics": {},
                "suggestions": [],
                "overall_score": 0,
            }
            
            # 2.1 资源利用度
            resource_utilization = min(1.0, chapter_data.get("resources_count", 0) / 6)  # 假设6种资源为满分
            evaluation["metrics"]["resource_utilization"] = round(resource_utilization, 2)
            
            # 2.2 学习时间效率
            learning_time = chapter_data.get("learning_time_minutes", 0)
            expected_time = 60  # 假设每章建议学习时间60分钟
            time_efficiency = min(1.0, learning_time / expected_time) if expected_time > 0 else 0
            evaluation["metrics"]["time_efficiency"] = round(time_efficiency, 2)
            
            # 2.3 知识点覆盖度
            knowledge_points_count = chapter_data.get("knowledge_points_count", 0)
            # 这里可以更精确地计算，暂时简化
            knowledge_coverage = min(1.0, knowledge_points_count / 10)  # 假设10个知识点为满分
            evaluation["metrics"]["knowledge_coverage"] = round(knowledge_coverage, 2)
            
            # 2.4 互动参与度
            qa_count = chapter_data.get("qa_count", 0)
            participation = min(1.0, qa_count / 5)  # 假设5次问答为满分
            evaluation["metrics"]["participation"] = round(participation, 2)
            
            # 3. 计算总分
            weights = {
                "resource_utilization": 0.3,
                "time_efficiency": 0.2,
                "knowledge_coverage": 0.3,
                "participation": 0.2,
            }
            
            overall_score = sum(
                evaluation["metrics"][metric] * weight
                for metric, weight in weights.items()
            )
            evaluation["overall_score"] = round(overall_score, 2)
            
            # 4. 生成建议
            if resource_utilization < 0.5:
                evaluation["suggestions"].append("建议多使用不同类型的学习资源")
            
            if time_efficiency < 0.5:
                evaluation["suggestions"].append("学习时间不足，建议增加学习时间")
            elif time_efficiency > 1.5:
                evaluation["suggestions"].append("学习时间过长，建议提高学习效率")
            
            if knowledge_coverage < 0.7:
                evaluation["suggestions"].append("建议完成更多知识点的学习")
            
            if participation < 0.5:
                evaluation["suggestions"].append("建议增加互动，如提问或参与讨论")
            
            if overall_score >= 0.8:
                evaluation["suggestions"].append("学习表现优秀，可以进入下一章节")
            elif overall_score >= 0.6:
                evaluation["suggestions"].append("学习表现良好，可以继续巩固当前章节")
            else:
                evaluation["suggestions"].append("建议加强当前章节的学习")
            
            return evaluation
            
        except Exception as e:
            logger.error(f"章节学习表现评估失败: {e}")
            return {"error": str(e)}

    async def track_chapter_task_progress(
        self,
        user_id: int,
        course_id: int,
        chapter_id: int,
        tasks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """记录章节任务完成状态，初始化或合并任务列表。

        在活跃学习路径的 path_data 中维护 chapter_tasks_{chapter_id} 结构，
        存储每步任务的状态、正确率等信息。

        Args:
            user_id: 用户ID
            course_id: 课程ID
            chapter_id: 章节ID
            tasks: 任务定义列表，每项含 task_id / task_type 等字段。
                   为 None 时仅查询当前进度状态。

        Returns:
            包含当前任务进度状态的字典。
        """
        try:
            async with async_session_factory() as db:
                path = (
                    await db.execute(
                        select(StudyPath).where(
                            StudyPath.user_id == user_id,
                            StudyPath.course_id == course_id,
                            StudyPath.is_active == True,
                        )
                    )
                ).scalar_one_or_none()

                if not path:
                    return {"error": "没有找到活跃的学习路径"}

                path_data = path.path_data
                chapter_key = f"chapter_tasks_{chapter_id}"

                if chapter_key not in path_data:
                    path_data[chapter_key] = {
                        "chapter_id": chapter_id,
                        "tasks": [],
                        "current_task_index": 0,
                        "total_tasks": 0,
                        "completion_rate": 0.0,
                        "average_correct_rate": 0.0,
                    }

                state = path_data[chapter_key]

                if tasks is not None:
                    existing_ids = {t["task_id"] for t in state["tasks"]}
                    for task in tasks:
                        if task["task_id"] not in existing_ids:
                            task.setdefault("status", "pending")
                            task.setdefault("started_at", None)
                            task.setdefault("completed_at", None)
                            task.setdefault("correct_rate", None)
                            task.setdefault("score", None)
                            state["tasks"].append(task)
                            existing_ids.add(task["task_id"])

                    state["total_tasks"] = len(state["tasks"])
                    completed = sum(1 for t in state["tasks"] if t["status"] == "completed")
                    state["completion_rate"] = (
                        round(completed / state["total_tasks"], 2)
                        if state["total_tasks"] > 0
                        else 0.0
                    )
                    correct_rates = [
                        t["correct_rate"]
                        for t in state["tasks"]
                        if t.get("correct_rate") is not None
                    ]
                    state["average_correct_rate"] = (
                        round(sum(correct_rates) / len(correct_rates), 2)
                        if correct_rates
                        else 0.0
                    )

                path.path_data = path_data
                await db.commit()

                return {
                    "success": True,
                    "chapter_id": chapter_id,
                    "tasks": state["tasks"],
                    "current_task_index": state["current_task_index"],
                    "total_tasks": state["total_tasks"],
                    "completion_rate": state["completion_rate"],
                    "average_correct_rate": state["average_correct_rate"],
                }

        except Exception as e:
            logger.error(f"章节任务进度跟踪失败: {e}")
            return {"error": str(e)}

    async def update_task_completion(
        self,
        user_id: int,
        course_id: int,
        chapter_id: int,
        task_id: str,
        status: str,
        correct_rate: float | None = None,
        score: float | None = None,
    ) -> dict[str, Any]:
        """更新任务完成状态、正确率，并根据正确率生成调整建议。

        当任务标记为 completed 时，自动记录完成时间、正确率和得分，
        重新计算章节完成率与平均正确率，并给出后续难度调整建议。

        Args:
            user_id: 用户ID
            course_id: 课程ID
            chapter_id: 章节ID
            task_id: 任务唯一标识
            status: 新状态 (pending / in_progress / completed)
            correct_rate: 正确率 0.0~1.0，仅练习(material/practice)任务使用
            score: 得分，仅测试(test)任务使用

        Returns:
            更新后的任务状态，含 adjustment 调整建议字段。
        """
        try:
            async with async_session_factory() as db:
                path = (
                    await db.execute(
                        select(StudyPath).where(
                            StudyPath.user_id == user_id,
                            StudyPath.course_id == course_id,
                            StudyPath.is_active == True,
                        )
                    )
                ).scalar_one_or_none()

                if not path:
                    return {"error": "没有找到活跃的学习路径"}

                path_data = path.path_data
                chapter_key = f"chapter_tasks_{chapter_id}"
                state = path_data.get(chapter_key)

                if not state:
                    return {"error": f"章节 {chapter_id} 尚未初始化任务跟踪，请先调用 track_chapter_task_progress"}

                # 查找并更新目标任务
                task_found = False
                now = datetime.now(timezone.utc).isoformat()
                for task in state["tasks"]:
                    if task["task_id"] == task_id:
                        task["status"] = status
                        if status == "in_progress":
                            task["started_at"] = now
                        elif status == "completed":
                            task["completed_at"] = now
                            if correct_rate is not None:
                                task["correct_rate"] = correct_rate
                            if score is not None:
                                task["score"] = score
                        task_found = True
                        break

                if not task_found:
                    return {"error": f"未找到任务 {task_id}"}

                # 重新计算汇总统计
                total = len(state["tasks"])
                completed = sum(1 for t in state["tasks"] if t["status"] == "completed")
                state["completion_rate"] = round(completed / total, 2) if total > 0 else 0.0

                correct_rates = [
                    t["correct_rate"]
                    for t in state["tasks"]
                    if t.get("correct_rate") is not None
                ]
                state["average_correct_rate"] = (
                    round(sum(correct_rates) / len(correct_rates), 2)
                    if correct_rates
                    else 0.0
                )

                # 完成时推进当前任务索引
                if status == "completed":
                    state["current_task_index"] = min(
                        state["current_task_index"] + 1,
                        total - 1 if total > 0 else 0,
                    )

                path.path_data = path_data
                await db.commit()

                # 根据正确率生成调整建议
                adjustment: dict[str, Any] | None = None
                if status == "completed" and correct_rate is not None:
                    if correct_rate < 0.5:
                        adjustment = {
                            "action": "review",
                            "reason": "正确率偏低（< 50%），建议回顾知识点并降低后续任务难度",
                            "difficulty_adjustment": -1,
                        }
                    elif correct_rate < 0.7:
                        adjustment = {
                            "action": "practice",
                            "reason": "正确率一般（50%~70%），建议增加练习量巩固",
                            "difficulty_adjustment": 0,
                        }
                    else:
                        adjustment = {
                            "action": "proceed",
                            "reason": "正确率良好（>= 70%），可以继续后续任务",
                            "difficulty_adjustment": 1,
                        }

                return {
                    "success": True,
                    "chapter_id": chapter_id,
                    "task_id": task_id,
                    "status": status,
                    "correct_rate": correct_rate,
                    "score": score,
                    "completion_rate": state["completion_rate"],
                    "average_correct_rate": state["average_correct_rate"],
                    "current_task_index": state["current_task_index"],
                    "total_tasks": total,
                    "adjustment": adjustment,
                }

        except Exception as e:
            logger.error(f"章节任务完成状态更新失败: {e}")
            return {"error": str(e)}

    async def get_chapter_progress_summary(
        self,
        user_id: int,
        course_id: int,
        chapter_id: int,
    ) -> dict[str, Any]:
        """获取章节进度摘要，供前端仪表盘展示。

        包含完成率、平均正确率、按任务类型的分布统计，
        以及基于已完成任务平均耗时估算的预计剩余时间。

        Args:
            user_id: 用户ID
            course_id: 课程ID
            chapter_id: 章节ID

        Returns:
            章节进度摘要字典。
        """
        try:
            async with async_session_factory() as db:
                path = (
                    await db.execute(
                        select(StudyPath).where(
                            StudyPath.user_id == user_id,
                            StudyPath.course_id == course_id,
                            StudyPath.is_active == True,
                        )
                    )
                ).scalar_one_or_none()

                if not path:
                    return {"error": "没有找到活跃的学习路径"}

                path_data = path.path_data
                chapter_key = f"chapter_tasks_{chapter_id}"
                state = path_data.get(chapter_key)

                if not state:
                    return {
                        "chapter_id": chapter_id,
                        "completion_rate": 0.0,
                        "average_correct_rate": 0.0,
                        "total_tasks": 0,
                        "completed_tasks": 0,
                        "current_task_index": 0,
                        "estimated_remaining_minutes": 0,
                        "task_type_breakdown": {},
                        "recent_completions": [],
                        "tasks": [],
                    }

                tasks = state["tasks"]
                total = len(tasks)
                completed_tasks = [t for t in tasks if t["status"] == "completed"]
                completed_count = len(completed_tasks)
                in_progress_count = sum(1 for t in tasks if t["status"] == "in_progress")

                # 按任务类型统计
                task_type_breakdown: dict[str, dict[str, Any]] = {}
                for task in tasks:
                    ttype = task.get("task_type", "unknown")
                    bucket = task_type_breakdown.setdefault(
                        ttype, {"total": 0, "completed": 0, "correct_rates": []}
                    )
                    bucket["total"] += 1
                    if task["status"] == "completed":
                        bucket["completed"] += 1
                        if task.get("correct_rate") is not None:
                            bucket["correct_rates"].append(task["correct_rate"])

                # 汇总各类型正确率
                for data in task_type_breakdown.values():
                    rates = data.pop("correct_rates")
                    data["average_correct_rate"] = (
                        round(sum(rates) / len(rates), 2) if rates else 0.0
                    )

                # 预计剩余时间（基于已完成任务的平均耗时）
                estimated_remaining_minutes = 0
                completed_with_time = [
                    t for t in completed_tasks
                    if t.get("started_at") and t.get("completed_at")
                ]
                if completed_with_time and completed_count < total:
                    total_duration = 0.0
                    for t in completed_with_time:
                        try:
                            started = datetime.fromisoformat(t["started_at"])
                            completed_dt = datetime.fromisoformat(t["completed_at"])
                            total_duration += (completed_dt - started).total_seconds() / 60
                        except (ValueError, TypeError):
                            continue
                    avg_time = total_duration / len(completed_with_time) if completed_with_time else 5.0
                    estimated_remaining_minutes = round(avg_time * (total - completed_count), 1)

                # 最近完成的任务（最多5条）
                recent_completions = sorted(
                    [
                        {
                            "task_id": t["task_id"],
                            "task_type": t.get("task_type", "unknown"),
                            "correct_rate": t.get("correct_rate"),
                            "score": t.get("score"),
                            "completed_at": t.get("completed_at"),
                        }
                        for t in completed_tasks
                        if t.get("completed_at")
                    ],
                    key=lambda x: x["completed_at"] or "",
                    reverse=True,
                )[:5]

                # extract individual task progress for frontend
                task_progress_list = [
                    {
                        "task_id": t["task_id"],
                        "status": t.get("status", "pending"),
                        "correct_rate": t.get("correct_rate"),
                        "score": t.get("score"),
                    }
                    for t in tasks
                ]

                return {
                    "chapter_id": chapter_id,
                    "total_tasks": total,
                    "completed_tasks": completed_count,
                    "in_progress_tasks": in_progress_count,
                    "pending_tasks": total - completed_count - in_progress_count,
                    "completion_rate": state.get("completion_rate", 0.0),
                    "average_correct_rate": state.get("average_correct_rate", 0.0),
                    "current_task_index": state.get("current_task_index", 0),
                    "estimated_remaining_minutes": estimated_remaining_minutes,
                    "task_type_breakdown": task_type_breakdown,
                    "recent_completions": recent_completions,
                    "tasks": task_progress_list,
                }

        except Exception as e:
            logger.error(f"获取章节进度摘要失败: {e}")
            return {"error": str(e)}

    @staticmethod
    def _course_dict(course: Course) -> dict[str, Any]:
        return {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "seed_course": course.seed_course,
        }

    @staticmethod
    def _chapter_dict(chapter: Chapter) -> dict[str, Any]:
        return {
            "id": chapter.id,
            "course_id": chapter.course_id,
            "title": chapter.title,
            "description": chapter.description,
            "sort_order": chapter.sort_order,
        }

    @staticmethod
    def _knowledge_point_dict(kp: KnowledgePoint) -> dict[str, Any]:
        return {
            "id": kp.id,
            "chapter_id": kp.chapter_id,
            "title": kp.title,
            "content": kp.content,
            "difficulty": kp.difficulty,
            "prerequisites": kp.prerequisites or [],
            "sort_order": kp.sort_order,
        }
