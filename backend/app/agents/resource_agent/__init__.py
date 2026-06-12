"""资源生成 Agent 群 - 6种子Agent并行协作 + ResourceCoordinator"""

from __future__ import annotations

import asyncio
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.llm_gateway import LLMGateway, LLMMessage
from app.models.learning_resource import LearningResource
from app.models.course import Course, Chapter
from app.models.knowledge_point import KnowledgePoint
from app.models.student_profile import StudentProfile
from app.agents.resource_agent.resource_agents import (
    DocumentAgent,
    MindMapAgent,
    ExerciseAgent,
    CodeAgent,
    ReadingAgent,
    VideoAgent,
)
from loguru import logger


class ResourceCoordinator:
    """资源生成协调器 - 统一入口，负责意图解析→知识匹配→并行派发→结果入库"""

    def __init__(self):
        self.llm = LLMGateway()
        self.agents = {
            "document": DocumentAgent(),
            "mindmap": MindMapAgent(),
            "exercise": ExerciseAgent(),
            "code": CodeAgent(),
            "reading": ReadingAgent(),
            "video": VideoAgent(),
        }

    async def process(self, state: dict) -> dict:
        """处理资源生成请求"""
        user_id = state["user_id"]
        message = state["message"]
        course_id = state.get("course_id")

        # 1. 获取用户画像（获取学习水平信息）
        level = "beginner"
        async with async_session_factory() as db:
            result = await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            if profile:
                pd = profile.profile_data
                level = pd.get("knowledge_base", {}).get("level", "beginner")

        # 2. 从消息中解析要生成的知识点主题
        knowledge_point, matched_chapter_id = await self._extract_topic(
            message=message, course_id=course_id, user_id=user_id,
        )

        # 3. 并行生成全部 6 种资源
        tasks = []
        for agent_type, agent in self.agents.items():
            params = {
                "knowledge_point": knowledge_point,
                "level": level,
                "course_id": course_id,
                "chapter_id": matched_chapter_id,
                "user_id": user_id,
                "learning_goal": f"掌握{knowledge_point}",
                "language": "python",
                "format": "分场景脚本",
            }
            tasks.append(self._generate_and_save(
                agent_type=agent_type, agent=agent, params=params,
                user_id=user_id, course_id=course_id, chapter_id=matched_chapter_id,
            ))

        results = await asyncio.gather(*tasks)

        # 4. 构建返回消息
        success = [r for r in results if r]
        resource_list = "\n".join([f"- {r['title']}" for r in success])

        return {
            "type": "resource",
            "message": (
                f"已为您生成《{knowledge_point}》相关学习资源（{len(success)}/6）：\n\n"
                f"{resource_list}\n\n"
                f"请前往「资源中心」查看完整内容。"
            ),
            "resources": success,
        }

    async def _extract_topic(self, message: str, course_id: int | None, user_id: int) -> tuple[str, int | None]:
        """从消息中提取知识点主题，尝试与数据库中现有知识点匹配"""
        async with async_session_factory() as db:
            # 获取课程列表
            course_query = select(Course).where(Course.is_active == True)
            if course_id:
                course_query = course_query.where(Course.id == course_id)
            result = await db.execute(course_query)
            courses = result.scalars().all()

            # 获取所有知识点
            kp_query = select(KnowledgePoint)
            if course_id:
                kp_query = kp_query.join(Chapter).where(Chapter.course_id == course_id)
            kp_result = await db.execute(kp_query.order_by(KnowledgePoint.sort_order))
            all_kps = kp_result.scalars().all()

            # 精确匹配
            for kp in all_kps:
                if kp.title.lower() in message.lower() or message.lower() in kp.title.lower():
                    return kp.title, kp.chapter_id

            # LLM 模糊匹配
            course_names = [c.title for c in courses]
            kp_names = [kp.title for kp in all_kps]
            prompt = (
                f"用户消息：{message}\n\n"
                f"可用课程：{', '.join(course_names) if course_names else '无'}\n"
                f"可用知识点：{', '.join(kp_names) if kp_names else '无'}\n\n"
                f"请从消息中提取要生成学习资源的【知识点主题】（简短，不超过20字）。"
                f"如果消息提到了具体的课程知识点，选择最匹配的知识点名称；"
                f"如果没提到，直接从消息中提取核心概念。只返回知识点名称。"
            )
            try:
                response = await self.llm.chat(
                    messages=[LLMMessage("user", prompt)],
                    temperature=0.3, max_tokens=100,
                )
                topic = response.content.strip().strip('"').strip("'")
                return topic or message[:30], None
            except Exception as e:
                logger.warning(f"LLM 主题提取失败: {e}")
                return message[:30], None

    async def _generate_and_save(self, agent_type: str, agent, params: dict,
                                  user_id: int, course_id: int | None, chapter_id: int | None) -> dict | None:
        """生成资源并保存到数据库"""
        try:
            result = await agent.generate(params)
            title = result.get("title", "")
            content = result.get("content", "")

            async with async_session_factory() as db:
                resource = LearningResource(
                    user_id=user_id,
                    course_id=course_id or 1,
                    chapter_id=chapter_id,
                    resource_type=agent_type,
                    title=title,
                    content=content,
                    is_generated=True,
                )
                db.add(resource)
                await db.commit()
                await db.refresh(resource)

            logger.info(f"资源已保存: {title}")
            return {"id": resource.id, "title": title, "type": agent_type}
        except Exception as e:
            logger.error(f"资源生成失败 ({agent_type}): {e}")
            return None


__all__ = [
    "DocumentAgent",
    "MindMapAgent",
    "ExerciseAgent",
    "CodeAgent",
    "ReadingAgent",
    "VideoAgent",
    "ResourceCoordinator",
]
