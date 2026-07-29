"""资源生成 Agent 群 - 6种子Agent并行协作 + ResourceCoordinator"""

from __future__ import annotations

import asyncio
import hashlib
import json
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
from app.agents.resource_agent.resource_reviewer import ResourceReviewer
from app.services.event_service import EventService, EventType
from app.services.student_state import StudentStateService
from loguru import logger


class ResourceCoordinator:
    """资源生成协调器 - 统一入口，负责意图解析→知识匹配→并行派发→结果入库"""

    VIDEO_GENERATOR_VERSION = "video_lesson_v3"
    VIDEO_PROMPT_VERSION = "video_prompt_v3"

    # 任务类型→资源类型映射
    TASK_RESOURCE_MAP: dict[str, list[str]] = {
        "preview": ["mindmap", "document"],
        "learn": [],  # 根据学生画像动态选择
        "practice": ["exercise", "code"],
        "review": ["mindmap", "document"],
        "exam": ["exercise"],
    }

    # 学习阶段→偏好→资源类型（用于 learn 任务）
    LEARN_RESOURCE_BY_PREFERENCE: dict[str, list[str]] = {
        "visual": ["video", "mindmap", "document"],
        "auditory": ["video", "document"],
        "practical": ["code", "exercise", "document"],
        "logical": ["exercise", "reading", "document"],
        "reading": ["reading", "document"],
    }

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
        self.reviewer = ResourceReviewer()
        self.student_state = StudentStateService()
    
    def _select_resource_types_by_profile(self, profile: dict, level: str) -> list[str]:
        """根据学生画像和水平选择最合适的资源类型"""
        # 默认资源类型
        default_types = ["document", "mindmap", "exercise"]
        
        # 根据认知风格调整资源类型
        cognitive_style = profile.get("cognitive_style", {})
        preference = cognitive_style.get("preference", "").lower()
        
        selected_types = list(default_types)
        
        # 视觉学习者：增加思维导图和视频
        if "视觉" in preference or "visual" in preference:
            if "mindmap" not in selected_types:
                selected_types.append("mindmap")
            if "video" not in selected_types:
                selected_types.append("video")
        
        # 听觉学习者：增加视频
        if "听觉" in preference or "auditory" in preference:
            if "video" not in selected_types:
                selected_types.append("video")
        
        # 实践学习者：增加代码案例和练习题
        if "实践" in preference or "practical" in preference:
            if "code" not in selected_types:
                selected_types.append("code")
            if "exercise" not in selected_types:
                selected_types.append("exercise")
        
        # 阅读学习者：增加拓展阅读
        if "阅读" in preference or "reading" in preference:
            if "reading" not in selected_types:
                selected_types.append("reading")
        
        # 根据水平调整
        if level in ("beginner", "入门"):
            # 初学者：增加文档和思维导图
            if "document" not in selected_types:
                selected_types.append("document")
            if "mindmap" not in selected_types:
                selected_types.append("mindmap")
        elif level in ("intermediate", "中级"):
            # 中级学习者：均衡分配
            pass
        elif level in ("advanced", "高级"):
            # 高级学习者：增加代码案例和拓展阅读
            if "code" not in selected_types:
                selected_types.append("code")
            if "reading" not in selected_types:
                selected_types.append("reading")
        
        # 确保至少包含3种资源类型
        if len(selected_types) < 3:
            for resource_type in ["document", "mindmap", "exercise", "video", "code", "reading"]:
                if resource_type not in selected_types:
                    selected_types.append(resource_type)
                if len(selected_types) >= 3:
                    break
        
        return selected_types[:6]  # 最多6种资源类型

    def get_resources_for_task(
        self,
        task_type: str,
        profile: dict | None = None,
        level: str = "beginner",
    ) -> list[str]:
        """根据任务类型返回需要的资源类型列表。

        Args:
            task_type: 任务类型 (preview / learn / practice / review / exam)
            profile: 学生画像数据，用于 learn 任务动态选择资源类型
            level: 学习水平 (beginner / intermediate / advanced)

        Returns:
            该任务类型需要的资源类型名称列表

        Raises:
            ValueError: 当 task_type 不在预定义的任务类型中时
        """
        if task_type not in self.TASK_RESOURCE_MAP:
            valid_types = list(self.TASK_RESOURCE_MAP.keys())
            msg = f"未知任务类型: {task_type}，有效值: {valid_types}"
            raise ValueError(msg)

        if task_type == "learn":
            # learn 类型需要根据学生画像动态选择
            resource_types = self._select_resource_types_for_learn(profile, level)
        else:
            resource_types = list(self.TASK_RESOURCE_MAP[task_type])

        # 根据学生水平调整（高级增加代码和阅读，初级保留文档和思维导图）
        if level in ("advanced", "高级"):
            for extra_type in ("code", "reading"):
                if extra_type not in resource_types:
                    resource_types.append(extra_type)
        elif level in ("beginner", "入门"):
            for extra_type in ("document", "mindmap"):
                if extra_type not in resource_types:
                    resource_types.append(extra_type)

        return resource_types

    def _select_resource_types_for_learn(
        self,
        profile: dict | None = None,
        level: str = "beginner",
    ) -> list[str]:
        """为 learn 任务类型选择资源类型，基于学生画像偏好。"""
        if not profile:
            return ["document", "mindmap", "exercise"]

        cognitive_style = profile.get("cognitive_style", {})
        preference = cognitive_style.get("preference", "").lower()

        # 根据认知偏好匹配资源类型
        preference_map: dict[str, list[str]] = {
            "视觉": ["video", "mindmap", "document"],
            "visual": ["video", "mindmap", "document"],
            "听觉": ["video", "document"],
            "auditory": ["video", "document"],
            "实践": ["code", "exercise", "document"],
            "practical": ["code", "exercise", "document"],
            "阅读": ["reading", "document"],
            "reading": ["reading", "document"],
            "逻辑": ["exercise", "reading", "document"],
            "logical": ["exercise", "reading", "document"],
        }

        for key, types in preference_map.items():
            if key in preference:
                result = list(types)
                if level in ("beginner", "入门") and "document" not in result:
                    result.append("document")
                return result

        # 无偏好匹配时返回默认
        return ["document", "mindmap", "exercise"]

    async def ensure_resources_for_knowledge_point(
        self,
        *,
        user_id: int,
        course_id: int,
        chapter_id: int | None,
        knowledge_point_id: int,
        knowledge_point: str,
        chapter_title: str | None = None,
        knowledge_point_full_title: str | None = None,
        knowledge_point_content: str | None = None,
        level: str = "beginner",
        resource_types: list[str] | None = None,
        student_state_snapshot_id: str | None = None,
        profile_version: int | None = None,
        profile: dict | None = None,
        task_type: str | None = None,
    ) -> list[dict]:
        """Return persisted resources for a knowledge point, generating missing types once.

        Args:
            task_type: 任务类型 (preview/learn/practice/review/exam)，
                       与 resource_types 二选一，task_type 优先级低于 resource_types
        """
        # 确定需要的资源类型：resource_types > task_type > 画像选择 > 全部
        if resource_types is not None:
            wanted_types = resource_types
        elif task_type is not None:
            # 按任务类型获取需要的资源类型
            if profile:
                wanted_types = self.get_resources_for_task(task_type, profile, level)
            else:
                try:
                    student_state = await self.student_state.load(user_id, course_id)
                    profile_data = student_state["profile"]["data"]
                    wanted_types = self.get_resources_for_task(task_type, profile_data, level)
                except Exception:
                    wanted_types = self.get_resources_for_task(task_type)
        else:
            # 无任务类型时，使用原有画像选择逻辑
            if profile:
                wanted_types = self._select_resource_types_by_profile(profile, level)
            else:
                try:
                    student_state = await self.student_state.load(user_id, course_id)
                    profile_data = student_state["profile"]["data"]
                    wanted_types = self._select_resource_types_by_profile(profile_data, level)
                except Exception:
                    wanted_types = list(self.agents.keys())
        async with async_session_factory() as db:
            result = await db.execute(
                select(LearningResource).where(
                    LearningResource.user_id == user_id,
                    LearningResource.course_id == course_id,
                    LearningResource.knowledge_point_id == knowledge_point_id,
                    LearningResource.resource_type.in_(wanted_types),
                )
            )
            existing = result.scalars().all()

        context_hash = self._context_hash(
            {
                "chapter_title": chapter_title,
                "knowledge_point_full_title": knowledge_point_full_title or knowledge_point,
                "knowledge_point_content": knowledge_point_content,
            }
        )
        existing_by_type = {
            resource.resource_type: resource
            for resource in existing
            if self._resource_is_current(
                resource,
                knowledge_point_full_title=knowledge_point_full_title or knowledge_point,
                knowledge_point=knowledge_point,
                context_hash=context_hash,
            )
        }
        tasks = []
        for agent_type in wanted_types:
            if agent_type in existing_by_type or agent_type not in self.agents:
                continue
            params = {
                "knowledge_point": knowledge_point,
                "level": level,
                "course_id": course_id,
                "chapter_id": chapter_id,
                "knowledge_point_id": knowledge_point_id,
                "chapter_title": chapter_title,
                "knowledge_point_full_title": knowledge_point_full_title or knowledge_point,
                "knowledge_point_content": knowledge_point_content,
                "user_id": user_id,
                "learning_goal": f"掌握{knowledge_point}",
                "language": "python",
                "format": "scene script",
                "student_state_snapshot_id": student_state_snapshot_id,
                "profile_version": profile_version,
            }
            tasks.append(
                self._generate_and_save(
                    agent_type=agent_type,
                    agent=self.agents[agent_type],
                    params=params,
                    user_id=user_id,
                    course_id=course_id,
                    chapter_id=chapter_id,
                    knowledge_point_id=knowledge_point_id,
                )
            )

        generated = [resource for resource in await asyncio.gather(*tasks) if resource] if tasks else []
        return [
            {
                "id": resource.id,
                "title": resource.title,
                "type": resource.resource_type,
                "content": resource.content,
            }
            for resource in existing_by_type.values()
        ] + generated

    @staticmethod
    def _resource_matches_params(
        resource: LearningResource,
        *,
        knowledge_point_full_title: str,
        knowledge_point: str,
    ) -> bool:
        metadata = resource.resource_metadata or {}
        return (
            metadata.get("knowledge_point_full_title") == knowledge_point_full_title
            or metadata.get("knowledge_point") == knowledge_point
        )

    @classmethod
    def _resource_is_current(
        cls,
        resource: LearningResource,
        *,
        knowledge_point_full_title: str,
        knowledge_point: str,
        context_hash: str | None = None,
    ) -> bool:
        if not cls._resource_matches_params(
            resource,
            knowledge_point_full_title=knowledge_point_full_title,
            knowledge_point=knowledge_point,
        ):
            return False
        if resource.resource_type != "video":
            return True
        metadata = resource.resource_metadata or {}
        if metadata.get("generator_version") != cls.VIDEO_GENERATOR_VERSION:
            return False
        if metadata.get("prompt_version") != cls.VIDEO_PROMPT_VERSION:
            return False
        if context_hash and metadata.get("context_hash") != context_hash:
            return False
        return cls._is_video_like_slides(resource.content)

    @staticmethod
    def _is_video_like_slides(content: str | None) -> bool:
        try:
            data = json.loads(content or "")
        except (TypeError, json.JSONDecodeError):
            return False
        if not (
            isinstance(data, dict)
            and data.get("mode") == "video_like_slides"
            and isinstance(data.get("slides"), list)
            and bool(data["slides"])
        ):
            return False
        try:
            VideoAgent._validate_video_quality(data["slides"])
        except ValueError:
            return False
        return True

    @staticmethod
    def _context_hash(params: dict) -> str:
        payload = {
            "chapter_title": params.get("chapter_title") or "",
            "knowledge_point_full_title": params.get("knowledge_point_full_title") or "",
            "knowledge_point_content": params.get("knowledge_point_content") or "",
        }
        return hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()

    async def _process_with_student_state(self, state: dict) -> dict:
        user_id = state["user_id"]
        message = state["message"]
        course_id = state.get("course_id")

        student_state = state.get("student_state") or await self.student_state.load(user_id, course_id)
        profile_data = student_state["profile"]["data"]
        level = profile_data.get("knowledge_base", {}).get("level", "beginner")
        course_context = student_state["course_context"]
        target_course = course_context.get("course")
        target_course_id = course_id or (target_course["id"] if target_course else None)

        knowledge_point, matched_chapter_id, matched_knowledge_point_id = await self._extract_topic_from_state(
            message=message,
            student_state=student_state,
        )
        chapter_titles = {
            chapter.get("id"): chapter.get("title")
            for chapter in course_context.get("chapters", [])
            if chapter.get("id")
        }
        matched_kp = next(
            (
                kp for kp in course_context.get("knowledge_points", [])
                if kp.get("id") == matched_knowledge_point_id
            ),
            {},
        )
        matched_chapter_title = chapter_titles.get(matched_chapter_id)
        matched_content = matched_kp.get("content") if isinstance(matched_kp, dict) else None

        tasks = []
        for agent_type, agent in self.agents.items():
            params = {
                "knowledge_point": knowledge_point,
                "level": level,
                "course_id": target_course_id,
                "chapter_id": matched_chapter_id,
                "knowledge_point_id": matched_knowledge_point_id,
                "chapter_title": matched_chapter_title,
                "knowledge_point_full_title": (
                    f"{matched_chapter_title} - {knowledge_point}"
                    if matched_chapter_title and knowledge_point
                    else knowledge_point
                ),
                "knowledge_point_content": matched_content,
                "user_id": user_id,
                "learning_goal": f"掌握{knowledge_point}",
                "language": "python",
                "format": "scene script",
                "student_state_snapshot_id": student_state["snapshot_id"],
                "profile_version": student_state["profile"]["version"],
            }
            tasks.append(self._generate_and_save(
                agent_type=agent_type,
                agent=agent,
                params=params,
                user_id=user_id,
                course_id=target_course_id,
                chapter_id=matched_chapter_id,
                knowledge_point_id=matched_knowledge_point_id,
            ))

        results = await asyncio.gather(*tasks)
        success = [result for result in results if result]
        resource_list = "\n".join([f"- {resource['title']}" for resource in success])
        return {
            "type": "resource",
            "message": (
                f"Generated resources for {knowledge_point} ({len(success)}/6):\n\n"
                f"{resource_list}"
            ),
            "resources": success,
            "student_state_snapshot_id": student_state["snapshot_id"],
        }

    async def _extract_topic_from_state(self, message: str, student_state: dict) -> tuple[str, int | None, int | None]:
        course_context = student_state["course_context"]
        all_kps = course_context.get("knowledge_points", [])
        for kp in all_kps:
            title = kp.get("title", "")
            if title and (title.lower() in message.lower() or message.lower() in title.lower()):
                return title, kp.get("chapter_id"), kp.get("id")

        course_names = [course["title"] for course in course_context.get("available_courses", [])]
        kp_names = [kp["title"] for kp in all_kps]
        prompt = (
            f"User request: {message}\n\n"
            f"Available courses: {', '.join(course_names) if course_names else 'none'}\n"
            f"Available knowledge points: {', '.join(kp_names) if kp_names else 'none'}\n\n"
            "Extract the short knowledge-point topic for learning resource generation. "
            "Return only the topic."
        )
        try:
            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                temperature=0.3,
                max_tokens=100,
            )
            topic = response.content.strip().strip('"').strip("'")
            return topic or message[:30], None, None
        except Exception as exc:
            logger.warning(f"Topic extraction from student state failed: {exc}")
            return message[:30], None, None

    async def process(self, state: dict) -> dict:
        """处理资源生成请求"""
        user_id = state["user_id"]
        message = state["message"]
        course_id = state.get("course_id")

        # 1. 获取用户画像（获取学习水平信息）
        try:
            return await self._process_with_student_state(state)
        except Exception as exc:
            logger.warning(f"Shared-state resource workflow failed; using legacy resource flow: {exc}")

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
        knowledge_point, matched_chapter_id, matched_knowledge_point_id = await self._extract_topic(
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
                "knowledge_point_id": matched_knowledge_point_id,
                "user_id": user_id,
                "learning_goal": f"掌握{knowledge_point}",
                "language": "python",
                "format": "分场景脚本",
            }
            tasks.append(self._generate_and_save(
                agent_type=agent_type, agent=agent, params=params,
                user_id=user_id, course_id=course_id, chapter_id=matched_chapter_id,
                knowledge_point_id=matched_knowledge_point_id,
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

    async def _extract_topic(self, message: str, course_id: int | None, user_id: int) -> tuple[str, int | None, int | None]:
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
                    return kp.title, kp.chapter_id, kp.id

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
                return topic or message[:30], None, None
            except Exception as e:
                logger.warning(f"LLM 主题提取失败: {e}")
                return message[:30], None, None

    async def _generate_and_save(self, agent_type: str, agent, params: dict,
                                  user_id: int, course_id: int | None, chapter_id: int | None,
                                  knowledge_point_id: int | None = None) -> dict | None:
        """生成资源、审查质量并保存到数据库"""
        try:
            result = await agent.generate(params)
            title = result.get("title", "")
            content = result.get("content", "")

            # Post-generation quality review
            review = self.reviewer.review(agent_type, content)

            async with async_session_factory() as db:
                existing = (
                    await db.execute(
                        select(LearningResource).where(
                            LearningResource.user_id == user_id,
                            LearningResource.course_id == (course_id or 1),
                            LearningResource.knowledge_point_id == knowledge_point_id,
                            LearningResource.resource_type == agent_type,
                        )
                    )
                ).scalar_one_or_none()
                metadata = {
                        "student_state_snapshot_id": params.get("student_state_snapshot_id"),
                        "profile_version": params.get("profile_version"),
                        "knowledge_point": params.get("knowledge_point"),
                        "knowledge_point_id": knowledge_point_id,
                        "chapter_title": params.get("chapter_title"),
                        "knowledge_point_full_title": params.get("knowledge_point_full_title"),
                        "knowledge_point_content": params.get("knowledge_point_content"),
                        "review_status": review.status,
                        "review_score": review.score,
                        "review_issues": review.issues,
                    }
                if agent_type == "video":
                    metadata.update(
                        {
                            "generator_version": self.VIDEO_GENERATOR_VERSION,
                            "prompt_version": self.VIDEO_PROMPT_VERSION,
                            "context_hash": self._context_hash(params),
                        }
                    )
                if existing:
                    resource = existing
                    resource.chapter_id = chapter_id
                    resource.title = title
                    resource.content = content
                    resource.resource_metadata = metadata
                    resource.is_generated = True
                else:
                    resource = LearningResource(
                        user_id=user_id,
                        course_id=course_id or 1,
                        chapter_id=chapter_id,
                        knowledge_point_id=knowledge_point_id,
                        resource_type=agent_type,
                        title=title,
                        content=content,
                        resource_metadata=metadata,
                        is_generated=True,
                    )
                    db.add(resource)
                await db.commit()
                await db.refresh(resource)

            logger.info(
                f"资源已保存: {title} (review: {review.status}, score: {review.score})"
            )
            await EventService.emit(
                user_id=user_id,
                course_id=course_id or 1,
                event_type=EventType.RESOURCE_GENERATED,
                source_agent=f"{agent_type.title()}Agent",
                target_type="learning_resource",
                target_id=resource.id,
                payload={
                    "resource_type": agent_type,
                    "title": title,
                    "chapter_id": chapter_id,
                    "knowledge_point_id": knowledge_point_id,
                    "student_state_snapshot_id": params.get("student_state_snapshot_id"),
                    "profile_version": params.get("profile_version"),
                    "knowledge_point": params.get("knowledge_point"),
                    "chapter_title": params.get("chapter_title"),
                    "knowledge_point_full_title": params.get("knowledge_point_full_title"),
                    "generator_version": metadata.get("generator_version"),
                    "prompt_version": metadata.get("prompt_version"),
                    "context_hash": metadata.get("context_hash"),
                    "review_status": review.status,
                    "review_score": review.score,
                    "review_issues": review.issues,
                },
            )
            return {
                "id": resource.id,
                "title": title,
                "type": agent_type,
                "content": content,
                "review_status": review.status,
                "review_score": review.score,
                "review_issues": review.issues,
            }
        except Exception as e:
            logger.error(f"资源生成失败 ({agent_type}): {e}")
            return None

    async def generate_chapter_preview_resources(
        self,
        *,
        user_id: int,
        course_id: int,
        chapter_id: int,
        chapter_title: str,
        knowledge_points: list[dict],
        level: str = "beginner",
        profile: dict | None = None,
    ) -> list[dict]:
        """为章节预览阶段生成资源"""
        try:
            # 1. 获取学生画像
            if profile is None:
                try:
                    student_state = await self.student_state.load(user_id, course_id)
                    profile = student_state["profile"]["data"]
                except Exception:
                    profile = {}
            
            # 2. 选择资源类型
            preview_types = ["mindmap", "document"]  # 预览阶段主要需要思维导图和概览文档
            
            # 3. 生成资源
            resources = []
            for resource_type in preview_types:
                if resource_type not in self.agents:
                    continue
                
                agent = self.agents[resource_type]
                params = {
                    "knowledge_point": f"章节预览：{chapter_title}",
                    "level": level,
                    "course_id": course_id,
                    "chapter_id": chapter_id,
                    "knowledge_point_id": None,
                    "chapter_title": chapter_title,
                    "knowledge_point_full_title": f"章节预览：{chapter_title}",
                    "knowledge_point_content": f"本章节包含以下知识点：{', '.join([kp.get('title', '') for kp in knowledge_points])}",
                    "user_id": user_id,
                    "learning_goal": f"快速了解{chapter_title}章节结构",
                    "language": "python",
                    "format": "章节预览",
                }
                
                result = await self._generate_and_save(
                    agent_type=resource_type,
                    agent=agent,
                    params=params,
                    user_id=user_id,
                    course_id=course_id,
                    chapter_id=chapter_id,
                    knowledge_point_id=None,
                )
                if result:
                    resources.append(result)
            
            return resources
            
        except Exception as e:
            logger.error(f"章节预览资源生成失败: {e}")
            return []

    async def generate_practice_resources(
        self,
        *,
        user_id: int,
        course_id: int,
        chapter_id: int,
        chapter_title: str,
        knowledge_points: list[dict],
        level: str = "beginner",
        practice_type: str = "basic",
    ) -> list[dict]:
        """为练习阶段生成资源"""
        try:
            # 1. 选择练习资源类型
            practice_types = ["exercise"]
            if level in ("intermediate", "中级", "advanced", "高级"):
                practice_types.append("code")
            
            # 2. 生成资源
            resources = []
            for resource_type in practice_types:
                if resource_type not in self.agents:
                    continue
                
                agent = self.agents[resource_type]
                params = {
                    "knowledge_point": f"章节练习：{chapter_title}",
                    "level": level,
                    "course_id": course_id,
                    "chapter_id": chapter_id,
                    "knowledge_point_id": None,
                    "chapter_title": chapter_title,
                    "knowledge_point_full_title": f"章节练习：{chapter_title}",
                    "knowledge_point_content": f"本章节包含以下知识点：{', '.join([kp.get('title', '') for kp in knowledge_points])}",
                    "user_id": user_id,
                    "learning_goal": f"通过练习巩固{chapter_title}章节知识",
                    "language": "python",
                    "format": "章节练习",
                }
                
                result = await self._generate_and_save(
                    agent_type=resource_type,
                    agent=agent,
                    params=params,
                    user_id=user_id,
                    course_id=course_id,
                    chapter_id=chapter_id,
                    knowledge_point_id=None,
                )
                if result:
                    resources.append(result)
            
            return resources
            
        except Exception as e:
            logger.error(f"章节练习资源生成失败: {e}")
            return []

    async def generate_review_resources(
        self,
        *,
        user_id: int,
        course_id: int,
        chapter_id: int,
        chapter_title: str,
        knowledge_points: list[dict],
        level: str = "beginner",
    ) -> list[dict]:
        """为复习阶段生成资源"""
        try:
            # 1. 选择复习资源类型
            review_types = ["mindmap", "document"]
            
            # 2. 生成资源
            resources = []
            for resource_type in review_types:
                if resource_type not in self.agents:
                    continue
                
                agent = self.agents[resource_type]
                params = {
                    "knowledge_point": f"章节复习：{chapter_title}",
                    "level": level,
                    "course_id": course_id,
                    "chapter_id": chapter_id,
                    "knowledge_point_id": None,
                    "chapter_title": chapter_title,
                    "knowledge_point_full_title": f"章节复习：{chapter_title}",
                    "knowledge_point_content": f"本章节包含以下知识点：{', '.join([kp.get('title', '') for kp in knowledge_points])}",
                    "user_id": user_id,
                    "learning_goal": f"复习巩固{chapter_title}章节所有知识点",
                    "language": "python",
                    "format": "章节复习",
                }
                
                result = await self._generate_and_save(
                    agent_type=resource_type,
                    agent=agent,
                    params=params,
                    user_id=user_id,
                    course_id=course_id,
                    chapter_id=chapter_id,
                    knowledge_point_id=None,
                )
                if result:
                    resources.append(result)
            
            return resources
            
        except Exception as e:
            logger.error(f"章节复习资源生成失败: {e}")
            return []


__all__ = [
    "DocumentAgent",
    "MindMapAgent",
    "ExerciseAgent",
    "CodeAgent",
    "ReadingAgent",
    "VideoAgent",
    "ResourceCoordinator",
]
