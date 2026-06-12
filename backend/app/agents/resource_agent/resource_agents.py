"""资源生成 Agent 群 - 6种子Agent，基于 LLM + 提示词模板 + 学习策略生成内容"""

from __future__ import annotations

from loguru import logger

from app.core.llm_gateway import LLMGateway, LLMMessage
from app.prompts.resource_prompts import (
    DOCUMENT_GENERATION_PROMPT,
    MINDMAP_GENERATION_PROMPT,
    EXERCISE_GENERATION_PROMPT,
    CODE_GENERATION_PROMPT,
    READING_GENERATION_PROMPT,
    VIDEO_GENERATION_PROMPT,
)
from app.services.retriever import Retriever
from app.services.learning_strategies import LearningStrategyEngine, LearningStrategy


class BaseResourceAgent:
    """资源生成基类"""

    def __init__(self):
        self.llm = LLMGateway()
        self.retriever = Retriever()
        self.strategy_engine = LearningStrategyEngine()

    async def generate(self, params: dict) -> dict:
        """生成资源（由子类实现）"""
        raise NotImplementedError

    def _inject_strategies(self, prompt: str, params: dict) -> str:
        """注入学习策略到提示词"""
        level = params.get("level", "beginner")
        strategies = []

        # 根据水平推荐策略
        if level in ("beginner", "入门"):
            strategies = [LearningStrategy.FEYNMAN_TECHNIQUE, LearningStrategy.DUAL_CODING]
        elif level in ("intermediate", "中级"):
            strategies = [LearningStrategy.ELABORATION, LearningStrategy.INTERLEAVING]
        elif level in ("advanced", "高级"):
            strategies = [LearningStrategy.ELABORATION, LearningStrategy.ACTIVE_RECALL]

        # 构建策略上下文
        context = {}
        for s in strategies:
            context = self.strategy_engine.apply(s, context)

        # 生成策略指令并注入
        strategy_prompt = self.strategy_engine.build_strategy_prompt(strategies, context)
        if strategy_prompt:
            prompt = f"{strategy_prompt}\n\n{prompt}"

        return prompt

    async def _build_context(self, params: dict) -> str:
        """构建 RAG 上下文"""
        knowledge_point = params.get("knowledge_point", "")
        course_id = params.get("course_id")
        context_parts = []

        # 如果有知识点，检索相关文档切片
        if knowledge_point:
            try:
                results = await self.retriever.retrieve(
                    query=knowledge_point,
                    course_id=course_id,
                    limit=3,
                    use_vector=False,
                )
                if results:
                    context_parts.append("相关资料：")
                    for r in results:
                        context_parts.append(r["content"])
            except Exception as e:
                logger.warning(f"RAG 检索失败: {e}")

        return "\n\n".join(context_parts)


class DocumentAgent(BaseResourceAgent):
    """课程讲义生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info(f"DocumentAgent: 开始生成讲义 - {params.get('knowledge_point', '')}")
        try:
            knowledge_point = params.get("knowledge_point", "")
            level = params.get("level", "beginner")
            context = await self._build_context(params)

            prompt = DOCUMENT_GENERATION_PROMPT.format(
                knowledge_point=knowledge_point,
                level=level,
            )
            # 注入学习策略
            prompt = self._inject_strategies(prompt, params)

            if context:
                prompt = f"{context}\n\n{prompt}"

            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system_prompt="你是一个专业的课程讲师，负责生成高质量的结构化讲义。请使用中文。",
                temperature=0.7,
                max_tokens=4096,
            )

            return {
                "type": "document",
                "title": f"{knowledge_point} - 课程讲义",
                "content": response.content,
            }
        except Exception as e:
            logger.error(f"DocumentAgent 错误: {e}")
            return {"type": "document", "title": "讲义生成失败", "content": f"生成失败：{str(e)}"}


class MindMapAgent(BaseResourceAgent):
    """思维导图生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info(f"MindMapAgent: 开始生成思维导图 - {params.get('knowledge_point', '')}")
        try:
            knowledge_point = params.get("knowledge_point", "")
            learning_goal = params.get("learning_goal", "掌握核心概念")

            prompt = MINDMAP_GENERATION_PROMPT.format(
                knowledge_point=knowledge_point,
                learning_goal=learning_goal,
            )
            # 双重编码策略对思维导图特别适用
            context = self.strategy_engine.apply(LearningStrategy.DUAL_CODING, {})
            prompt = (
                f"{context.get('prompt_instructions', '')}\n\n{prompt}"
            )

            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system_prompt="你是一个思维导图设计师。请直接返回 Mermaid 代码块。",
                temperature=0.5,
                max_tokens=2048,
            )

            return {
                "type": "mindmap",
                "title": f"{knowledge_point} - 思维导图",
                "content": response.content,
            }
        except Exception as e:
            logger.error(f"MindMapAgent 错误: {e}")
            return {"type": "mindmap", "title": "思维导图生成失败", "content": f"生成失败：{str(e)}"}


class ExerciseAgent(BaseResourceAgent):
    """练习题生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info(f"ExerciseAgent: 开始生成练习题 - {params.get('knowledge_point', '')}")
        try:
            knowledge_point = params.get("knowledge_point", "")
            level = params.get("level", "beginner")

            prompt = EXERCISE_GENERATION_PROMPT.format(
                knowledge_point=knowledge_point,
                level=level,
            )
            # 交错练习策略对练习题特别适用
            context = self.strategy_engine.apply(LearningStrategy.INTERLEAVING, {})
            prompt = f"{context.get('prompt_instructions', '')}\n\n{prompt}"

            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system_prompt="你是一个出题专家。请生成高质量的练习题，附参考答案和解析。使用中文。",
                temperature=0.6,
                max_tokens=4096,
            )

            return {
                "type": "exercise",
                "title": f"{knowledge_point} - 练习题",
                "content": response.content,
            }
        except Exception as e:
            logger.error(f"ExerciseAgent 错误: {e}")
            return {"type": "exercise", "title": "练习题生成失败", "content": f"生成失败：{str(e)}"}


class CodeAgent(BaseResourceAgent):
    """代码案例生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info(f"CodeAgent: 开始生成代码案例 - {params.get('knowledge_point', '')}")
        try:
            knowledge_point = params.get("knowledge_point", "")
            language = params.get("language", "python")

            prompt = CODE_GENERATION_PROMPT.format(
                knowledge_point=knowledge_point,
                language=language,
            )

            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system_prompt="你是一个编程导师。请生成完整可运行的代码示例，加中文注释。",
                temperature=0.5,
                max_tokens=4096,
            )

            return {
                "type": "code",
                "title": f"{knowledge_point} - 代码案例",
                "content": response.content,
            }
        except Exception as e:
            logger.error(f"CodeAgent 错误: {e}")
            return {"type": "code", "title": "代码生成失败", "content": f"生成失败：{str(e)}"}


class ReadingAgent(BaseResourceAgent):
    """拓展阅读生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info(f"ReadingAgent: 开始生成拓展阅读 - {params.get('knowledge_point', '')}")
        try:
            knowledge_point = params.get("knowledge_point", "")
            level = params.get("level", "beginner")

            prompt = READING_GENERATION_PROMPT.format(
                topic=knowledge_point,
                level=level,
            )
            # 精细加工策略对拓展阅读特别适用
            context = self.strategy_engine.apply(LearningStrategy.ELABORATION, {})
            prompt = f"{context.get('prompt_instructions', '')}\n\n{prompt}"

            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system_prompt="你是一个学术阅读导师。推荐高质量的学习材料并说明关联。使用中文。",
                temperature=0.7,
                max_tokens=3072,
            )

            return {
                "type": "reading",
                "title": f"{knowledge_point} - 拓展阅读",
                "content": response.content,
            }
        except Exception as e:
            logger.error(f"ReadingAgent 错误: {e}")
            return {"type": "reading", "title": "拓展阅读生成失败", "content": f"生成失败：{str(e)}"}


class VideoAgent(BaseResourceAgent):
    """教学动画脚本生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info(f"VideoAgent: 开始生成视频脚本 - {params.get('knowledge_point', '')}")
        try:
            knowledge_point = params.get("knowledge_point", "")
            script_format = params.get("format", "分场景脚本")

            prompt = VIDEO_GENERATION_PROMPT.format(
                knowledge_point=knowledge_point,
                format=script_format,
            )
            # 双重编码策略对视频脚本特别适用
            context = self.strategy_engine.apply(LearningStrategy.DUAL_CODING, {})
            prompt = f"{context.get('prompt_instructions', '')}\n\n{prompt}"

            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system_prompt="你是一个教学动画脚本作者。生成包含场景描述和旁白的详细脚本。使用中文。",
                temperature=0.7,
                max_tokens=4096,
            )

            return {
                "type": "video",
                "title": f"{knowledge_point} - 教学动画脚本",
                "content": response.content,
            }
        except Exception as e:
            logger.error(f"VideoAgent 错误: {e}")
            return {"type": "video", "title": "视频脚本生成失败", "content": f"生成失败：{str(e)}"}
