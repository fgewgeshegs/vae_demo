"""资源生成 Agent 群 - 6种子Agent并行协作"""

from app.agents.resource_agent.resource_agents import (
    DocumentAgent,
    MindMapAgent,
    ExerciseAgent,
    CodeAgent,
    ReadingAgent,
    VideoAgent,
)

__all__ = [
    "DocumentAgent",
    "MindMapAgent",
    "ExerciseAgent",
    "CodeAgent",
    "ReadingAgent",
    "VideoAgent",
]
