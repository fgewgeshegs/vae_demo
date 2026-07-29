"""Create a one-time, data-backed learning baseline for user1.

The generated records use the normal business tables, so later user actions and
agent outputs continue the same history instead of replacing a visual demo.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.core.database import async_session_factory
from app.models import (
    Chapter,
    Course,
    Evaluation,
    KnowledgePoint,
    LearningBehavior,
    LearningEvent,
    LearningResource,
    QARecord,
    StudentProfile,
    StudyPath,
    User,
)


SEED_SOURCE = "user1_baseline_v1"


def at_day(day_offset: int, hour: int, minute: int = 0) -> datetime:
    now = datetime.now(timezone.utc)
    return (now + timedelta(days=day_offset)).replace(hour=hour, minute=minute, second=0, microsecond=0)


async def main() -> None:
    async with async_session_factory() as session:
        user = (await session.execute(select(User).where(User.username == "user1"))).scalar_one_or_none()
        if not user:
            raise RuntimeError("User 'user1' was not found. Register or create it before seeding.")

        marker = (
            await session.execute(
                select(LearningEvent.id).where(
                    LearningEvent.user_id == user.id,
                    LearningEvent.source_agent == SEED_SOURCE,
                    LearningEvent.event_type == "baseline_initialized",
                )
            )
        ).scalar_one_or_none()
        if marker:
            print("Baseline already exists for user1; no records were added.")
            return

        course = (await session.execute(select(Course).where(Course.title == "人工智能导论"))).scalar_one_or_none()
        if not course:
            course = Course(
                title="人工智能导论",
                description="从 AI 基础、机器学习概念到神经网络与负责任 AI 的入门课程。",
                seed_course=True,
                is_active=True,
            )
            session.add(course)
            await session.flush()

        chapters = (await session.execute(select(Chapter).where(Chapter.course_id == course.id).order_by(Chapter.sort_order))).scalars().all()
        if not chapters:
            chapters = [
                Chapter(course_id=course.id, title="人工智能概述", description="理解 AI 的定义、应用和基本方法。", sort_order=1),
                Chapter(course_id=course.id, title="机器学习基础", description="认识数据、特征、训练与评估。", sort_order=2),
                Chapter(course_id=course.id, title="神经网络入门", description="理解神经网络的基本结构与训练过程。", sort_order=3),
            ]
            session.add_all(chapters)
            await session.flush()

        first_chapter = chapters[0]
        knowledge_points = (await session.execute(select(KnowledgePoint).where(KnowledgePoint.chapter_id == first_chapter.id))).scalars().all()
        if not knowledge_points:
            knowledge_points = [
                KnowledgePoint(chapter_id=first_chapter.id, title="人工智能的定义与边界", content="区分 AI、自动化与传统程序。", difficulty="easy", sort_order=1),
                KnowledgePoint(chapter_id=first_chapter.id, title="监督学习与分类任务", content="理解样本、标签、特征和分类结果。", difficulty="medium", sort_order=2),
            ]
            session.add_all(knowledge_points)
            await session.flush()

        profile_data = {
            "knowledge_base": {"level": "beginner", "subjects": ["Python 基础", "简单数据结构"]},
            "cognitive_style": {"preference": "visual", "description": "偏好结合案例、图示与简短练习理解概念。"},
            "learning_goals": {
                "short_term": "4 周完成 AI 基础，理解机器学习基本概念。",
                "long_term": "完成一个简单分类练习，并具备继续学习机器学习的基础。",
            },
            "learning_pace": {"speed": "normal", "preferred_session_minutes": 45, "preferred_time": "20:00-21:00"},
            "interest_direction": {"areas": ["机器学习", "大语言模型", "AI 应用开发"]},
            "knowledge_gaps": ["数学基础", "模型原理"],
            "weak_points": ["学习连续性", "矩阵与向量概念"],
        }
        profile = (await session.execute(select(StudentProfile).where(StudentProfile.user_id == user.id))).scalar_one_or_none()
        if profile:
            profile.profile_data = profile_data
            profile.version += 1
        else:
            session.add(StudentProfile(user_id=user.id, profile_data=profile_data, version=1))

        await session.execute(update(StudyPath).where(StudyPath.user_id == user.id, StudyPath.is_active.is_(True)).values(is_active=False))
        nodes = [
            {"id": "ai-01", "title": "AI 的定义与应用边界", "type": "preview", "difficulty": "easy", "estimated_minutes": 25, "status": "completed", "chapter_title": "人工智能概述"},
            {"id": "ai-02", "title": "监督学习与分类任务", "type": "learn", "difficulty": "medium", "estimated_minutes": 45, "status": "completed", "chapter_title": "机器学习基础"},
            {"id": "ai-03", "title": "特征、标签与训练集", "type": "learn", "difficulty": "medium", "estimated_minutes": 40, "status": "in_progress", "chapter_title": "机器学习基础"},
            {"id": "ai-04", "title": "分类模型练习", "type": "practice", "difficulty": "medium", "estimated_minutes": 35, "status": "pending", "chapter_title": "机器学习基础"},
            {"id": "ai-05", "title": "矩阵与向量复习", "type": "review", "difficulty": "medium", "estimated_minutes": 30, "status": "pending", "chapter_title": "数学基础"},
            {"id": "ai-06", "title": "神经网络的基本结构", "type": "learn", "difficulty": "medium", "estimated_minutes": 45, "status": "pending", "chapter_title": "神经网络入门"},
            {"id": "ai-07", "title": "损失函数与模型训练", "type": "learn", "difficulty": "medium", "estimated_minutes": 40, "status": "pending", "chapter_title": "神经网络入门"},
            {"id": "ai-08", "title": "简单分类器实践", "type": "practice", "difficulty": "medium", "estimated_minutes": 50, "status": "pending", "chapter_title": "机器学习基础"},
            {"id": "ai-09", "title": "AI 伦理与安全", "type": "review", "difficulty": "easy", "estimated_minutes": 25, "status": "pending", "chapter_title": "负责任 AI"},
            {"id": "ai-10", "title": "AI 基础阶段测验", "type": "exam", "difficulty": "medium", "estimated_minutes": 30, "status": "pending", "chapter_title": "阶段复盘"},
        ]
        path = StudyPath(
            user_id=user.id,
            course_id=course.id,
            progress=0.2,
            is_active=True,
            path_data={"course_title": course.title, "current_index": 2, "nodes": nodes, "goal": profile_data["learning_goals"]["short_term"]},
        )
        session.add(path)

        resource_specs = [
            ("document", "AI 基础概念速览", "用一页内容梳理人工智能、机器学习和深度学习的关系。"),
            ("mindmap", "机器学习分类任务思维导图", "从数据、特征、标签到模型评估的结构化知识图。"),
            ("exercise", "监督学习入门练习", "5 道分类任务基础题，附带简短解析。"),
            ("video", "特征与标签：5 分钟微课", "通过一个垃圾邮件分类案例理解特征与标签。"),
        ]
        resources = [
            LearningResource(user_id=user.id, course_id=course.id, chapter_id=first_chapter.id, knowledge_point_id=knowledge_points[0].id, resource_type=kind, title=title, content=content, resource_metadata={"baseline": True, "estimated_minutes": 10}, is_generated=kind != "document")
            for kind, title, content in resource_specs
        ]
        session.add_all(resources)
        await session.flush()

        session.add_all([
            QARecord(user_id=user.id, course_id=course.id, question="监督学习和传统编程有什么区别？", answer="传统编程由人写规则；监督学习从带标签的样本中学习规则。", resource_ids=[resources[0].id], qa_metadata={"sources": [{"source": "AI 基础概念速览", "locator": "监督学习"}]}),
            QARecord(user_id=user.id, course_id=course.id, question="为什么分类任务需要标签？", answer="标签告诉模型每个训练样本的正确类别，模型才能学习输入与输出之间的对应关系。", resource_ids=[resources[2].id], qa_metadata={"sources": [{"source": "监督学习入门练习", "locator": "第 2 题"}]}),
        ])

        evaluation_dates = [at_day(-14, 20), at_day(-7, 20), at_day(0, 20)]
        evaluation_scores = [
            {"knowledge_mastery": 32, "learning_efficiency": 38, "engagement": 48, "consistency": 30, "improvement": 35},
            {"knowledge_mastery": 40, "learning_efficiency": 48, "engagement": 60, "consistency": 42, "improvement": 58},
            {"knowledge_mastery": 48, "learning_efficiency": 56, "engagement": 70, "consistency": 50, "improvement": 68},
        ]
        for created_at, scores in zip(evaluation_dates, evaluation_scores):
            session.add(Evaluation(user_id=user.id, course_id=course.id, scores=scores, suggestions=["先完成矩阵与向量复习，再进入神经网络章节。", "保持每次 45 分钟的学习节奏，本周至少完成 3 次学习。"], strategy_signals={"next_focus": "巩固数学基础与分类任务练习"}, report_data={"method": "baseline", "baseline": True}, created_at=created_at))

        daily_baseline = [(-6, 20, 25, 1), (-5, 20, 45, 2), (-3, 21, 30, 1), (-2, 20, 55, 2), (-1, 20, 40, 1), (0, 20, 20, 1)]
        for day, hour, minutes, completed in daily_baseline:
            timestamp = at_day(day, hour)
            session.add(LearningBehavior(user_id=user.id, action_type="start_learning", target_type="study_path", target_id=path.id, behavior_metadata={"baseline": True, "completed_tasks": completed, "focus_level": "high" if minutes >= 45 else "medium"}, duration_seconds=minutes * 60, created_at=timestamp))
            session.add(LearningBehavior(user_id=user.id, action_type="complete_learning", target_type="study_path", target_id=path.id, behavior_metadata={"baseline": True, "completed_tasks": completed}, duration_seconds=0, created_at=timestamp + timedelta(minutes=minutes)))

        session.add(LearningEvent(user_id=user.id, course_id=course.id, event_type="baseline_initialized", source_agent=SEED_SOURCE, target_type="study_path", target_id=path.id, payload={"version": 1, "profile": "AI beginner", "days": 7}, status="completed", processed_at=datetime.now(timezone.utc)))
        await session.commit()
        print(f"Created a complete learning baseline for user1 (user_id={user.id}, course_id={course.id}, path_id={path.id}).")


if __name__ == "__main__":
    asyncio.run(main())
