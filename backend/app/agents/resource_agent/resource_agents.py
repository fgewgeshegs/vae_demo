"""资源生成 Agent 群 - 6种子Agent"""

from __future__ import annotations

from loguru import logger


class BaseResourceAgent:
    """资源生成基类"""

    async def generate(self, params: dict) -> dict:
        """生成资源（由子类实现）"""
        raise NotImplementedError


class DocumentAgent(BaseResourceAgent):
    """课程讲义生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info("DocumentAgent: 讲义生成将在 Phase 4 实现")
        return {"type": "document", "content": "生成结构化 Markdown 讲义"}


class MindMapAgent(BaseResourceAgent):
    """思维导图生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info("MindMapAgent: 思维导图将在 Phase 4 实现")
        return {"type": "mindmap", "content": "生成 Mermaid 语法思维导图"}


class ExerciseAgent(BaseResourceAgent):
    """练习题生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info("ExerciseAgent: 练习题将在 Phase 4 实现")
        return {"type": "exercise", "content": "生成选择题/填空题/简答题/编程题"}


class CodeAgent(BaseResourceAgent):
    """代码案例生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info("CodeAgent: 代码案例将在 Phase 4 实现")
        return {"type": "code", "content": "生成含注释的代码实操案例"}


class ReadingAgent(BaseResourceAgent):
    """拓展阅读生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info("ReadingAgent: 拓展阅读将在 Phase 4 实现")
        return {"type": "reading", "content": "生成论文导读/延伸概念"}


class VideoAgent(BaseResourceAgent):
    """教学动画脚本 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info("VideoAgent: 视频脚本将在 Phase 4 实现")
        return {"type": "video", "content": "生成 Manim 语法教学动画脚本"}
