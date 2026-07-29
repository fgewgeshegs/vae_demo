"""路径规划 Agent - 基于画像 + 课程知识图谱 + 学习策略生成个性化学习路径"""

from __future__ import annotations

import json
import re

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.llm_gateway import LLMGateway, LLMMessage
from app.models.study_path import StudyPath
from app.models.course import Course, Chapter
from app.models.evaluation import Evaluation
from app.models.knowledge_point import KnowledgePoint
from app.models.student_profile import StudentProfile
from app.agents.resource_agent import ResourceCoordinator
from app.services.event_service import EventService, EventType
from app.services.learning_strategies import LearningStrategyEngine, LearningStrategy
from app.services.student_state import StudentStateService
from loguru import logger

SHARED_RESOURCE_USER_ID = 1


PATH_GENERATION_PROMPT = """你是一个学习路径规划专家。请根据以下信息生成个性化的学习路径。

学习者画像：
{profile_summary}

课程信息：
{course_info}

知识点列表：
{knowledge_points}

{strategy_instructions}

{evaluation_context}
要求：
1. 将知识点组织为**逐步递进的学习节点**，每个节点对应一个知识点
2. 每个节点包含：title（名称）、type（preview/learn/practice/review/exam）、estimated_minutes（预计分钟数）
3. 根据学习者水平调整难度和节奏
4. 如果存在前置依赖，确保前置知识点排在前面
5. 总节点数控制在 8-15 个
6. 在适当位置插入复习节点和实践节点
7. 应用学习策略来优化学习顺序和方法
8. 如果提供了评估反馈，必须根据反馈调整节点类型分布和难度
9. 在章节开始时添加章节预览节点（preview类型），帮助学习者建立知识框架

请以 JSON 格式输出，格式如下：
{{
    "nodes": [
        {{"title": "章节预览：章节名称", "type": "preview", "estimated_minutes": 8}},
        {{"title": "知识点名称", "type": "learn", "estimated_minutes": 30}},
        {{"title": "复习：知识点名称", "type": "review", "estimated_minutes": 15}},
        ...
    ],
    "estimated_total_minutes": 总分钟数,
    "description": "路径总体说明"
}}

只返回 JSON，不要其他内容。
"""


class PathAgent:
    """路径规划 Agent"""

    def __init__(self):
        self.llm = LLMGateway()
        self.strategy_engine = LearningStrategyEngine()
        self.student_state = StudentStateService()
        self.resource_coordinator = ResourceCoordinator()

    @staticmethod
    def _item_value(item, key: str, default=None):
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)

    @staticmethod
    def _clean_title(title: str) -> str:
        cleaned = (title or "").strip().lower()
        for prefix in (
            "practice:",
            "review:",
            "综合练习：",
            "章节复习：",
            "复习：",
            "练习：",
        ):
            cleaned = cleaned.replace(prefix.lower(), "")
        return re.sub(r"\s+", "", cleaned).strip()

    @staticmethod
    def _title_aliases(title: str, chapter_title: str | None = None) -> set[str]:
        cleaned = PathAgent._clean_title(title)
        aliases = {cleaned} if cleaned else set()
        for separator in (" - ", "-", "：", ":", "–", "—"):
            if separator in cleaned:
                aliases.add(cleaned.split(separator)[-1].strip())
        if chapter_title:
            chapter_clean = PathAgent._clean_title(chapter_title)
            if chapter_clean and cleaned.startswith(chapter_clean):
                aliases.add(cleaned[len(chapter_clean):].strip(" -:：–—"))
            if chapter_clean and cleaned:
                aliases.add(f"{chapter_clean} - {cleaned}".strip())
        return {alias for alias in aliases if alias}

    @staticmethod
    def _build_evaluation_context(latest_evaluation: dict | None) -> str:
        """Build prompt context from the latest evaluation's strategy_signals.

        Returns an empty string when no evaluation is available so the prompt
        template degrades gracefully.
        """
        if not latest_evaluation:
            return ""
        signals = latest_evaluation.get("strategy_signals", {})
        if not signals:
            return ""
        parts = ["【最近评估反馈】根据最近的学习评估，请调整学习路径："]
        if signals.get("review_suggested"):
            parts.append("- 需要加强复习，在路径中增加复习节点（review 类型）")
        difficulty = signals.get("difficulty_change", "same")
        if difficulty == "easier":
            parts.append("- 当前难度偏高，请降低学习材料难度，从基础概念开始，增加 learn 类型节点")
        elif difficulty == "harder":
            parts.append("- 基础扎实，可以适当提高难度，增加挑战性内容和 exam 类型节点")
        if signals.get("adjust_pace"):
            parts.append("- 学习节奏需要放缓，减少每个节点的 estimated_minutes")
        if signals.get("feynman_suggested"):
            parts.append("- 使用费曼学习法：用简单语言解释概念，增加 practice 类型节点用于自我解释")
        if signals.get("recall_suggested"):
            parts.append("- 增加主动回忆环节，在 learn 节点前插入 recall 类型的预热节点")
        next_actions = signals.get("next_actions", [])
        if next_actions:
            parts.append("- 具体行动指令：")
            for action in next_actions:
                parts.append(f"  * {action.get('action', '')}: {action.get('reason', '')}")
        return "\n".join(parts)

    @staticmethod
    def _apply_evaluation_strategies(
        strategies: list[LearningStrategy],
        latest_evaluation: dict | None,
    ) -> list[LearningStrategy]:
        """Augment the strategy list based on evaluation signals.

        Returns a new list; does not mutate the input.
        """
        if not latest_evaluation:
            return list(strategies)
        signals = latest_evaluation.get("strategy_signals", {})
        if not signals:
            return list(strategies)
        result = list(strategies)
        if signals.get("review_suggested") and LearningStrategy.SPACED_REPETITION not in result:
            result.append(LearningStrategy.SPACED_REPETITION)
        if signals.get("feynman_suggested") and LearningStrategy.FEYNMAN_TECHNIQUE not in result:
            result.append(LearningStrategy.FEYNMAN_TECHNIQUE)
        if signals.get("recall_suggested") and LearningStrategy.ACTIVE_RECALL not in result:
            result.append(LearningStrategy.ACTIVE_RECALL)
        return result

    def _normalize_nodes(
        self,
        nodes: list[dict],
        *,
        course_context: dict | None = None,
        chapters_with_kps: list[tuple] | None = None,
    ) -> list[dict]:
        """Attach stable course anchors to path nodes so the UI can open real learning content."""
        kp_items: list[dict] = []
        chapter_titles: dict[str, int] = {}

        if course_context:
            for chapter in course_context.get("chapters", []):
                chapter_id = chapter.get("id")
                chapter_title = chapter.get("title", "")
                if chapter_id and chapter_title:
                    chapter_titles[chapter_title.lower()] = chapter_id
                for kp in chapter.get("knowledge_points", []):
                    item = dict(kp)
                    item.setdefault("chapter_title", chapter_title)
                    kp_items.append(item)

        if chapters_with_kps:
            for chapter_title, kps in chapters_with_kps:
                for kp in kps:
                    kp_items.append(
                        {
                            "id": self._item_value(kp, "id"),
                            "chapter_id": self._item_value(kp, "chapter_id"),
                            "chapter_title": chapter_title,
                            "title": self._item_value(kp, "title", str(kp)),
                            "content": self._item_value(kp, "content"),
                            "difficulty": self._item_value(kp, "difficulty"),
                        }
                    )

        by_id = {kp.get("id"): kp for kp in kp_items if kp.get("id")}
        by_title = {}
        for kp in kp_items:
            title = kp.get("title", "")
            if not title:
                continue
            for alias in self._title_aliases(title, kp.get("chapter_title")):
                by_title[alias] = kp

        normalized: list[dict] = []
        last_kp: dict | None = None
        for index, raw_node in enumerate(nodes or []):
            node = dict(raw_node) if isinstance(raw_node, dict) else {"title": str(raw_node)}
            title = str(node.get("title") or f"学习节点 {index + 1}")
            node_type = node.get("type") or "learn"
            clean_title = self._clean_title(title)

            kp = by_id.get(node.get("knowledge_point_id"))
            if not kp:
                kp = by_title.get(clean_title)
            if not kp:
                kp = next(
                    (
                        item
                        for key, item in by_title.items()
                        if key and (key in clean_title or clean_title in key)
                    ),
                    None,
                )
            if not kp and node_type in ("practice", "review"):
                kp = last_kp

            chapter_id = node.get("chapter_id")
            if not chapter_id and kp:
                chapter_id = kp.get("chapter_id")
            if not chapter_id:
                chapter_id = next(
                    (
                        value
                        for chapter_title, value in chapter_titles.items()
                        if chapter_title and chapter_title in clean_title
                    ),
                    None,
                )

            if kp and node_type == "learn":
                last_kp = kp
            chapter_title = (kp or {}).get("chapter_title")
            knowledge_point_title = (kp or {}).get("title")

            normalized.append(
                {
                    **node,
                    "id": node.get("id") or f"node-{index + 1}",
                    "title": title,
                    "type": node_type,
                    "status": node.get("status") or ("in_progress" if index == 0 else "pending"),
                    "estimated_minutes": int(node.get("estimated_minutes") or 30),
                    "chapter_id": chapter_id,
                    "knowledge_point_id": kp.get("id") if kp else node.get("knowledge_point_id"),
                    "chapter_title": node.get("chapter_title") or chapter_title,
                    "knowledge_point_title": node.get("knowledge_point_title") or knowledge_point_title,
                    "learning_content": node.get("learning_content") or (kp or {}).get("content"),
                    "difficulty": node.get("difficulty") or (kp or {}).get("difficulty"),
                    "resource_ids": [],
                }
            )
        return normalized

    async def _attach_resources_to_nodes(
        self,
        *,
        nodes: list[dict],
        user_id: int,
        course_id: int,
        level: str,
        student_state_snapshot_id: str | None = None,
        profile_version: int | None = None,
    ) -> list[dict]:
        for node in nodes:
            if node.get("type") != "learn" or not node.get("knowledge_point_id"):
                continue
            resources = await self.resource_coordinator.ensure_resources_for_knowledge_point(
                user_id=user_id,
                course_id=course_id,
                chapter_id=node.get("chapter_id"),
                knowledge_point_id=node["knowledge_point_id"],
                knowledge_point=node.get("knowledge_point_title") or node["title"],
                chapter_title=node.get("chapter_title"),
                knowledge_point_full_title=node["title"],
                knowledge_point_content=node.get("learning_content"),
                level=level,
                student_state_snapshot_id=student_state_snapshot_id,
                profile_version=profile_version,
            )
            node["resource_ids"] = [resource["id"] for resource in resources]
            if not node.get("learning_content"):
                resource_content = next(
                    (
                        resource.get("content")
                        for resource in resources
                        if resource.get("type") == "document" and resource.get("content")
                    ),
                    None,
                ) or next(
                    (
                        resource.get("content")
                        for resource in resources
                        if resource.get("content")
                    ),
                    None,
                )
                if resource_content:
                    node["learning_content"] = resource_content
        return nodes

    async def _ensure_course_resources(
        self,
        *,
        course_context: dict,
        user_id: int,
        course_id: int,
        level: str,
        student_state_snapshot_id: str | None = None,
        profile_version: int | None = None,
    ) -> dict[int, list[dict]]:
        resources_by_kp: dict[int, list[dict]] = {}
        chapter_titles = {
            chapter.get("id"): chapter.get("title")
            for chapter in course_context.get("chapters", [])
            if chapter.get("id")
        }
        for kp in course_context.get("knowledge_points", []):
            kp_id = kp.get("id")
            if not kp_id:
                continue
            chapter_title = kp.get("chapter_title") or chapter_titles.get(kp.get("chapter_id"))
            resources_by_kp[kp_id] = await self.resource_coordinator.ensure_resources_for_knowledge_point(
                user_id=SHARED_RESOURCE_USER_ID,
                course_id=course_id,
                chapter_id=kp.get("chapter_id"),
                knowledge_point_id=kp_id,
                chapter_title=chapter_title,
                knowledge_point_full_title=(
                    f"{chapter_title} - {kp.get('title')}"
                    if chapter_title and kp.get("title")
                    else kp.get("title")
                ),
                knowledge_point_content=kp.get("content"),
                knowledge_point=kp.get("title") or f"知识点 {kp_id}",
                level=level,
                student_state_snapshot_id=student_state_snapshot_id,
                profile_version=profile_version,
            )
        return resources_by_kp

    @staticmethod
    def _apply_resource_index_to_nodes(nodes: list[dict], resources_by_kp: dict[int, list[dict]]) -> list[dict]:
        for node in nodes:
            kp_id = node.get("knowledge_point_id")
            if not kp_id:
                continue
            resources = resources_by_kp.get(kp_id, [])
            if resources:
                node["resource_ids"] = [resource["id"] for resource in resources if resource.get("id")]
        return nodes

    async def generate_chapter_learning_plan(
        self,
        chapter_info: dict,
        profile: dict,
        evaluation_context: str | None = None,
    ) -> dict:
        """根据学生画像生成个性化的章节学习计划。

        分析学生水平、认知风格和评估反馈，生成包含预览、学习、
        练习、复习和测试环节的任务流，并推荐合适的资源类型。

        Args:
            chapter_info: 章节信息，包含 title、knowledge_points 列表等
            profile: 学生画像数据，至少包含 knowledge_base、cognitive_style
            evaluation_context: 可选的评估反馈上下文文本

        Returns:
            dict: {
                "tasks": list[dict],           # 任务列表
                "estimated_total_minutes": int, # 预计总耗时
                "description": str,             # 计划说明
            }
        """
        chapter_title = chapter_info.get("title", "")
        knowledge_points = chapter_info.get("knowledge_points", [])
        kp_count = len(knowledge_points)

        # 1. 分析学生画像
        level = profile.get("knowledge_base", {}).get("level", "beginner")
        cognitive_style = profile.get("cognitive_style", {})
        preference = cognitive_style.get("preference", "").lower()
        knowledge_gaps = profile.get("knowledge_gaps", [])

        # 对章节知识点进行难度分析
        hard_kp_count = sum(
            1 for kp in knowledge_points
            if isinstance(kp, dict) and kp.get("difficulty") in ("hard", "困难")
        )
        has_complex_concepts = hard_kp_count > 0

        # 2. 根据学生水平确定时间基准和学习节奏
        if level in ("beginner", "入门"):
            learn_minutes = 25       # 初学者学习速度较慢
            practice_minutes = 20
            preview_minutes = 10     # 更长的预览以建立框架
            review_minutes = 15      # 更长的复习巩固
            exam_minutes = 20
            practice_interval = 2    # 每 2 个知识点后安排练习
        elif level in ("advanced", "高级"):
            learn_minutes = 20       # 高效学习者吸收更快
            practice_minutes = 25    # 但练习深度更大
            preview_minutes = 5      # 快速预览
            review_minutes = 10      # 针对性复习
            exam_minutes = 30        # 更有挑战的测试
            practice_interval = 3    # 每 3 个知识点后安排综合练习
        else:  # intermediate / 中级
            learn_minutes = 25
            practice_minutes = 20
            preview_minutes = 8
            review_minutes = 12
            exam_minutes = 25
            practice_interval = 3

        # 困难知识点较多时延长学习时间
        if has_complex_concepts:
            learn_minutes = int(learn_minutes * 1.3)

        # 知识短板：增加预览和复习时间
        if knowledge_gaps:
            preview_minutes = int(preview_minutes * 1.3)
            review_minutes = int(review_minutes * 1.3)

        # 3. 根据认知风格确定推荐资源类型
        recommended_resource_types: list[str] = ["document"]  # 基础：文档

        if "视觉" in preference or "visual" in preference:
            recommended_resource_types.extend(["video", "mindmap"])
        if "实践" in preference or "practical" in preference:
            recommended_resource_types.extend(["code", "exercise"])
        if "逻辑" in preference or "logical" in preference:
            recommended_resource_types.extend(["exercise", "reading"])
        if "阅读" in preference or "reading" in preference:
            recommended_resource_types.append("reading")
        if "听觉" in preference or "auditory" in preference:
            if "video" not in recommended_resource_types:
                recommended_resource_types.append("video")

        # 去重并保持顺序
        seen: set[str] = set()
        resource_types: list[str] = []
        for r in recommended_resource_types:
            if r not in seen:
                seen.add(r)
                resource_types.append(r)

        # 4. 构建任务流
        tasks: list[dict] = []

        # 4a 章节预览
        tasks.append({
            "title": f"章节预览：{chapter_title}",
            "type": "preview",
            "estimated_minutes": max(5, preview_minutes),
            "resource_types": ["mindmap", "document"] if "mindmap" in resource_types else ["document"],
            "description": "了解本章学习目标、知识结构和学习路线",
        })

        # 4b 知识点学习 + 练习任务
        for i, kp in enumerate(knowledge_points):
            kp_title = kp.get("title", "") if isinstance(kp, dict) else str(kp)
            kp_difficulty = kp.get("difficulty", "medium") if isinstance(kp, dict) else "medium"

            # 根据知识点难度调整学习时间
            kp_minutes = learn_minutes
            if kp_difficulty in ("hard", "困难"):
                kp_minutes = int(kp_minutes * 1.4)
            elif kp_difficulty in ("easy", "简单"):
                kp_minutes = int(kp_minutes * 0.7)

            tasks.append({
                "title": kp_title,
                "type": "learn",
                "estimated_minutes": max(10, kp_minutes),
                "resource_types": resource_types,
                "difficulty": kp_difficulty,
            })

            # 每 practice_interval 个知识点后插入练习任务（最后一组不重复追加）
            if (i + 1) % practice_interval == 0 and (i + 1) < kp_count:
                tasks.append({
                    "title": f"综合练习：{chapter_title} - 第{(i + 1) // practice_interval}组",
                    "type": "practice",
                    "estimated_minutes": max(10, practice_minutes),
                    "resource_types": (
                        ["exercise", "code"]
                        if "code" in resource_types
                        else ["exercise"]
                    ),
                    "description": f"巩固前{(i + 1)}个知识点的内容",
                })

        # 4c 章节复习
        tasks.append({
            "title": f"章节复习：{chapter_title}",
            "type": "review",
            "estimated_minutes": max(10, review_minutes),
            "resource_types": ["mindmap", "document"] if "mindmap" in resource_types else ["document"],
            "description": "系统回顾本章全部知识点，查漏补缺",
        })

        # 4d 章节测试
        tasks.append({
            "title": f"章节测试：{chapter_title}",
            "type": "exam",
            "estimated_minutes": max(10, exam_minutes),
            "resource_types": ["exercise"],
            "description": "检验本章学习成果，评估掌握程度",
        })

        # 5. 计算总时间
        estimated_total = sum(task.get("estimated_minutes", 0) for task in tasks)

        # 6. 构建计划说明
        level_labels = {
            "beginner": "入门", "intermediate": "中级", "advanced": "高级",
            "入门": "入门", "中级": "中级", "高级": "高级",
        }
        level_label = level_labels.get(level, level)
        preference_label = preference if preference else "综合型"

        description = (
            f"为{level_label}水平学习者定制的《{chapter_title}》章节学习计划，"
            f"共{kp_count}个知识点、{len(tasks)}个任务，"
            f"预计{estimated_total}分钟。"
            f"适配{preference_label}学习风格，"
            f"推荐资源类型：{'、'.join(resource_types)}。"
        )

        # 附加评估反馈（如有）
        if evaluation_context:
            description += f"\n{evaluation_context}"

        return {
            "tasks": tasks,
            "estimated_total_minutes": estimated_total,
            "description": description,
        }

    def _generate_mock_path(self, course, chapters_with_kps: list[tuple]) -> dict:
        """生成模拟学习路径（当 LLM 不可用时的降级方案）"""
        nodes = []

        for ch_title, kps in chapters_with_kps:
            ch_key = ch_title.split("】")[-1].split("]")[-1].strip()  # 兼容 【/】 和 [/] 两种括号
            for i, kp in enumerate(kps):
                title = kp.title if hasattr(kp, 'title') else str(kp)
                nodes.append({
                    "title": title,
                    "type": "learn",
                    "estimated_minutes": 30,
                })

                # 每 3 个知识点后加一个练习节点
                if (i + 1) % 3 == 0:
                    nodes.append({
                        "title": f"综合练习：{title}",
                        "type": "practice",
                        "estimated_minutes": 20,
                    })

            # 每章末尾加一个复习节点
            if kps:
                nodes.append({
                    "title": f"章节复习：{ch_key}",
                    "type": "review",
                    "estimated_minutes": 15,
                })

        # 如果节点太少，补充一些通用节点
        if len(nodes) < 4:
            nodes.extend([
                {"title": "知识梳理与总结", "type": "review", "estimated_minutes": 20},
                {"title": "综合测试", "type": "exam", "estimated_minutes": 30},
            ])

        estimated_total = sum(n.get("estimated_minutes", 0) for n in nodes)
        return {
            "nodes": nodes,
            "estimated_total_minutes": estimated_total,
            "description": f"基于《{course.title}》课程生成的个性化学习路径，包含 {len(nodes)} 个学习节点，涵盖知识点学习、章节练习和复习巩固。",
        }

    async def _process_with_student_state(self, state: dict) -> dict:
        user_id = state["user_id"]
        course_id = state.get("course_id")
        student_state = state.get("student_state") or await self.student_state.load(user_id, course_id)
        profile_data = student_state["profile"]["data"]
        course_context = student_state["course_context"]
        target_course = course_context.get("course")
        if not target_course:
            return {
                "type": "path",
                "message": "No available course data. Create a course before generating a study path.",
            }

        profile_summary = await self.student_state.profile_summary(user_id, target_course["id"])
        course_info = (
            f"course: {target_course['title']}\n"
            f"description: {target_course.get('description') or 'none'}"
        )
        chapters_with_kps = [
            (chapter["title"], chapter.get("knowledge_points", []))
            for chapter in course_context.get("chapters", [])
        ]
        kp_items = []
        for chapter_title, kps in chapters_with_kps:
            for kp in kps:
                kp_items.append(
                    f"[{chapter_title}] {kp['title']} "
                    f"(difficulty: {kp.get('difficulty', 'medium')})"
                )
        kp_text = "\n".join(kp_items) if kp_items else "No knowledge point data."

        level = profile_data.get("knowledge_base", {}).get("level", "beginner")
        if level in ("beginner", "鍏ラ棬"):
            strategies = [LearningStrategy.SPACED_REPETITION, LearningStrategy.FEYNMAN_TECHNIQUE]
        elif level in ("intermediate", "涓骇"):
            strategies = [LearningStrategy.SPACED_REPETITION, LearningStrategy.INTERLEAVING, LearningStrategy.ACTIVE_RECALL]
        else:
            strategies = [LearningStrategy.SPACED_REPETITION, LearningStrategy.ELABORATION, LearningStrategy.INTERLEAVING]

        strategy_context = {}
        for strategy in strategies:
            strategy_context = self.strategy_engine.apply(strategy, strategy_context)

        # --- 评估反馈驱动：将最近评估的策略信号注入路径生成 ---
        latest_evaluation = student_state.get("latest_evaluation")
        evaluation_context = self._build_evaluation_context(latest_evaluation)
        strategies = self._apply_evaluation_strategies(strategies, latest_evaluation)
        if latest_evaluation:
            strategy_instructions = self.strategy_engine.build_strategy_prompt(strategies, strategy_context)

        try:
            prompt = PATH_GENERATION_PROMPT.format(
                profile_summary=profile_summary,
                course_info=course_info,
                knowledge_points=kp_text,
                strategy_instructions=strategy_instructions,
                evaluation_context=evaluation_context,
            )
            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system_prompt="You are a learning path planning expert. Return strict JSON only.",
                temperature=0.6,
                max_tokens=4096,
            )
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            path_data = json.loads(content)
            nodes = path_data.get("nodes", [])
            estimated_total = path_data.get("estimated_total_minutes", 0)
            description = path_data.get("description", "")
        except Exception as exc:
            logger.warning(f"Path generation from student state failed; using fallback: {exc}")
            # 评估驱动的降级路径：根据最近评估信号调整节点生成
            signals = (latest_evaluation or {}).get("strategy_signals", {})
            review_suggested = signals.get("review_suggested", False)
            difficulty_change = signals.get("difficulty_change", "same")
            adjust_pace = signals.get("adjust_pace", False)
            base_minutes = 20 if adjust_pace else 30
            review_interval = 2 if review_suggested else 3
            nodes = []
            for chapter_title, kps in chapters_with_kps:
                for index, kp in enumerate(kps):
                    node_type = "learn"
                    node_minutes = base_minutes
                    if difficulty_change == "easier":
                        node_minutes = max(15, base_minutes - 5)
                    elif difficulty_change == "harder":
                        node_minutes = min(45, base_minutes + 10)
                    nodes.append({
                        "title": kp["title"],
                        "type": node_type,
                        "estimated_minutes": node_minutes,
                    })
                    if (index + 1) % review_interval == 0:
                        nodes.append({
                            "title": f"Practice: {kp['title']}",
                            "type": "practice",
                            "estimated_minutes": max(10, node_minutes - 10),
                        })
                if kps:
                    nodes.append({
                        "title": f"Review: {chapter_title}",
                        "type": "review",
                        "estimated_minutes": 15,
                    })
            if len(nodes) < 4:
                nodes.extend([
                    {"title": "Knowledge review", "type": "review", "estimated_minutes": 20},
                    {"title": "Comprehensive quiz", "type": "exam", "estimated_minutes": 30},
                ])
            estimated_total = sum(node.get("estimated_minutes", 0) for node in nodes)
            description = (
                f"Generated from shared student state snapshot {student_state['snapshot_id']}."
            )

        nodes = self._normalize_nodes(nodes, course_context=course_context)
        estimated_total = sum(node.get("estimated_minutes", 0) for node in nodes)

        async with async_session_factory() as db:
            existing = await db.execute(
                select(StudyPath).where(
                    StudyPath.user_id == user_id,
                    StudyPath.course_id == target_course["id"],
                    StudyPath.is_active == True,
                )
            )
            old_path = existing.scalar_one_or_none()
            if old_path:
                old_path.is_active = False
                await db.flush()

            study_path = StudyPath(
                user_id=user_id,
                course_id=target_course["id"],
                path_data={
                    "nodes": nodes,
                    "current_index": 0,
                    "estimated_total_minutes": estimated_total,
                    "description": description,
                    "course_title": target_course["title"],
                    "strategies_applied": [strategy.value for strategy in strategies],
                    "student_state_snapshot_id": student_state["snapshot_id"],
                    "profile_version": student_state["profile"]["version"],
                },
                progress=0.0,
                is_active=True,
            )
            db.add(study_path)
            await db.commit()
            await db.refresh(study_path)
        await EventService.emit(
            user_id=user_id,
            course_id=target_course["id"],
            event_type=EventType.PATH_GENERATED,
            source_agent="PathAgent",
            target_type="study_path",
            target_id=study_path.id,
            payload={
                "node_count": len(nodes),
                "estimated_total_minutes": estimated_total,
                "student_state_snapshot_id": student_state["snapshot_id"],
                "profile_version": student_state["profile"]["version"],
            },
        )

        return {
            "type": "path",
            "message": f"Generated a study path for {target_course['title']} with {len(nodes)} nodes.",
            "path_id": study_path.id,
            "student_state_snapshot_id": student_state["snapshot_id"],
        }

    async def process(self, state: dict) -> dict:
        """生成学习路径"""
        user_id = state["user_id"]
        course_id = state.get("course_id")
        message = state.get("message", "")

        try:
            return await self._process_with_student_state(state)
        except Exception as exc:
            logger.warning(f"Shared-state path workflow failed; using legacy path flow: {exc}")

        try:
            # 1. 获取用户画像和学习数据
            profile_summary = "新用户"
            async with async_session_factory() as db:
                result = await db.execute(
                    select(StudentProfile).where(StudentProfile.user_id == user_id)
                )
                profile = result.scalar_one_or_none()
                profile_data = {}
                if profile:
                    pd = profile.profile_data
                    profile_data = pd
                    profile_summary = (
                        f"知识水平：{pd.get('knowledge_base', {}).get('level', '未知')}\n"
                        f"认知风格：{pd.get('cognitive_style', {}).get('preference', '未知')}\n"
                        f"学习目标：{pd.get('learning_goals', {}).get('short_term', '未设置')}\n"
                        f"兴趣方向：{', '.join(pd.get('interest_direction', {}).get('areas', [])) or '未知'}\n"
                        f"知识短板：{', '.join(pd.get('knowledge_gaps', [])) or '未知'}"
                    )

                # 2. 获取课程信息
                course_query = select(Course).where(Course.is_active == True)
                if course_id:
                    course_query = course_query.where(Course.id == course_id)
                result = await db.execute(course_query)
                courses = result.scalars().all()

                if not courses:
                    return {"type": "path", "message": "暂无可用课程，请先创建课程或上传学习资料。"}

                # 选择最相关的课程
                target_course = None
                if course_id:
                    for c in courses:
                        if c.id == course_id:
                            target_course = c
                            break

                if not target_course:
                    for c in courses:
                        if c.title.lower() in message.lower():
                            target_course = c
                            break

                if not target_course:
                    target_course = courses[0]

                course_info = f"课程名称：{target_course.title}\n课程描述：{target_course.description or '无'}"

                # 3. 获取知识点
                chapter_result = await db.execute(
                    select(Chapter).where(Chapter.course_id == target_course.id)
                    .order_by(Chapter.sort_order)
                )
                chapters = chapter_result.scalars().all()

                kp_list = []
                chapters_with_kps = []
                for ch in chapters:
                    kp_result = await db.execute(
                        select(KnowledgePoint).where(KnowledgePoint.chapter_id == ch.id)
                        .order_by(KnowledgePoint.sort_order)
                    )
                    ch_kps = kp_result.scalars().all()
                    chapters_with_kps.append((ch.title, ch_kps))
                    for kp in ch_kps:
                        kp_list.append(f"[{ch.title}] {kp.title}（难度：{kp.difficulty}）")

                kp_text = "\n".join(kp_list) if kp_list else "暂无知识点数据"

                # 加载最近评估用于路径调整
                eval_result = await db.execute(
                    select(Evaluation).where(
                        Evaluation.user_id == user_id,
                    ).order_by(Evaluation.created_at.desc()).limit(1)
                )
                latest_eval_row = eval_result.scalar_one_or_none()
                latest_evaluation = {
                    "id": latest_eval_row.id,
                    "scores": latest_eval_row.scores,
                    "suggestions": latest_eval_row.suggestions or [],
                    "strategy_signals": latest_eval_row.strategy_signals or {},
                } if latest_eval_row else None

            # 4. 应用学习策略
            level = profile_data.get("knowledge_base", {}).get("level", "beginner")
            if level in ("beginner", "入门"):
                strategies = [LearningStrategy.SPACED_REPETITION, LearningStrategy.FEYNMAN_TECHNIQUE]
            elif level in ("intermediate", "中级"):
                strategies = [LearningStrategy.SPACED_REPETITION, LearningStrategy.INTERLEAVING, LearningStrategy.ACTIVE_RECALL]
            else:
                strategies = [LearningStrategy.SPACED_REPETITION, LearningStrategy.ELABORATION, LearningStrategy.INTERLEAVING]

            # 构建策略上下文
            strategy_context = {}
            for s in strategies:
                strategy_context = self.strategy_engine.apply(s, strategy_context)

            # --- 评估反馈驱动：将最近评估的策略信号注入路径生成 ---
            evaluation_context = self._build_evaluation_context(latest_evaluation)
            strategies = self._apply_evaluation_strategies(strategies, latest_evaluation)
            if latest_evaluation:
                strategy_instructions = self.strategy_engine.build_strategy_prompt(strategies, strategy_context)

            # 5. 调用 LLM 生成路径
            prompt = PATH_GENERATION_PROMPT.format(
                profile_summary=profile_summary,
                course_info=course_info,
                knowledge_points=kp_text,
                strategy_instructions=strategy_instructions,
                evaluation_context=evaluation_context,
            )

            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system_prompt="你是学习路径规划专家。请根据学习者和课程信息，生成最有效的个性化学习路径。用中文输出JSON。",
                temperature=0.6,
                max_tokens=4096,
            )

            # 6. 解析 LLM 返回
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            path_data = json.loads(content)
            nodes = path_data.get("nodes", [])
            estimated_total = path_data.get("estimated_total_minutes", 0)
            description = path_data.get("description", "")

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"LLM 路径规划失败，使用 Mock 降级数据: {e}")
            # 降级：使用 Mock 数据生成学习路径
            # 检查是否已有 target_course（可能在 DB 操作阶段就出错了）
            target_course = locals().get('target_course')
            if target_course is None:
                return {"type": "path", "message": "暂无可用课程数据，请先创建课程后再生成学习路径。"}

            try:
                _ = chapters_with_kps
            except NameError:
                chapters_with_kps = []

            # 评估驱动的降级路径
            signals = (latest_evaluation or {}).get("strategy_signals", {})
            mock_path = self._generate_mock_path(target_course, chapters_with_kps)
            nodes = mock_path["nodes"]
            estimated_total = mock_path["estimated_total_minutes"]
            description = mock_path["description"]
            strategies = [LearningStrategy.SPACED_REPETITION, LearningStrategy.FEYNMAN_TECHNIQUE]
            strategies = self._apply_evaluation_strategies(strategies, latest_evaluation)

        nodes = self._normalize_nodes(nodes, chapters_with_kps=chapters_with_kps)
        nodes = await self._attach_resources_to_nodes(
            nodes=nodes,
            user_id=user_id,
            course_id=target_course.id,
            level=level,
        )
        estimated_total = sum(node.get("estimated_minutes", 0) for node in nodes)

        # 7. 保存到数据库（统一保存，无论 LLM 成功还是降级）
        try:
            async with async_session_factory() as db:
                existing = await db.execute(
                    select(StudyPath).where(
                        StudyPath.user_id == user_id,
                        StudyPath.course_id == target_course.id,
                        StudyPath.is_active == True,
                    )
                )
                old_path = existing.scalar_one_or_none()
                if old_path:
                    old_path.is_active = False
                    await db.flush()

                study_path = StudyPath(
                    user_id=user_id,
                    course_id=target_course.id,
                    path_data={
                        "nodes": nodes,
                        "current_index": 0,
                        "estimated_total_minutes": estimated_total,
                        "description": description,
                        "course_title": target_course.title,
                        "strategies_applied": [s.value for s in strategies],
                    },
                    progress=0.0,
                    is_active=True,
                )
                db.add(study_path)
                await db.commit()
                await db.refresh(study_path)
            await EventService.emit(
                user_id=user_id,
                course_id=target_course.id,
                event_type=EventType.PATH_GENERATED,
                source_agent="PathAgent",
                target_type="study_path",
                target_id=study_path.id,
                payload={
                    "node_count": len(nodes),
                    "estimated_total_minutes": estimated_total,
                    "legacy_flow": True,
                },
            )

            return {
                "type": "path",
                "message": (
                    f"已为您生成《{target_course.title}》学习路径！\n\n"
                    f"📚 共 {len(nodes)} 个学习节点，预计总时长 {estimated_total} 分钟\n"
                    f"{description}\n\n"
                    f"策略应用：已结合您的学习风格应用了相关学习策略\n"
                    f"请前往「学习路径」页面查看详细计划。"
                ),
                "path_id": study_path.id,
            }
        except Exception as e:
            logger.error(f"PathAgent 保存失败: {e}")
            return {"type": "path", "message": f"路径规划保存失败：{str(e)}"}
