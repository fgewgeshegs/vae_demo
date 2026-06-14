"""路径规划 Agent - 基于画像 + 课程知识图谱 + 学习策略生成个性化学习路径"""

from __future__ import annotations

import json

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.llm_gateway import LLMGateway, LLMMessage
from app.models.study_path import StudyPath
from app.models.course import Course, Chapter
from app.models.knowledge_point import KnowledgePoint
from app.models.student_profile import StudentProfile
from app.services.learning_strategies import LearningStrategyEngine, LearningStrategy
from loguru import logger


PATH_GENERATION_PROMPT = """你是一个学习路径规划专家。请根据以下信息生成个性化的学习路径。

学习者画像：
{profile_summary}

课程信息：
{course_info}

知识点列表：
{knowledge_points}

{strategy_instructions}

要求：
1. 将知识点组织为**逐步递进的学习节点**，每个节点对应一个知识点
2. 每个节点包含：title（名称）、type（learn/practice/review/exam）、estimated_minutes（预计分钟数）
3. 根据学习者水平调整难度和节奏
4. 如果存在前置依赖，确保前置知识点排在前面
5. 总节点数控制在 8-15 个
6. 在适当位置插入复习节点和实践节点
7. 应用学习策略来优化学习顺序和方法

请以 JSON 格式输出，格式如下：
{{
    "nodes": [
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

    async def process(self, state: dict) -> dict:
        """生成学习路径"""
        user_id = state["user_id"]
        course_id = state.get("course_id")
        message = state.get("message", "")

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
            strategy_instructions = self.strategy_engine.build_strategy_prompt(strategies, strategy_context)

            # 5. 调用 LLM 生成路径
            prompt = PATH_GENERATION_PROMPT.format(
                profile_summary=profile_summary,
                course_info=course_info,
                knowledge_points=kp_text,
                strategy_instructions=strategy_instructions,
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

            mock_path = self._generate_mock_path(target_course, chapters_with_kps)
            nodes = mock_path["nodes"]
            estimated_total = mock_path["estimated_total_minutes"]
            description = mock_path["description"]
            strategies = [LearningStrategy.SPACED_REPETITION, LearningStrategy.FEYNMAN_TECHNIQUE]

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
