"""智能辅导 Agent - RAG + 多模态回答"""

from __future__ import annotations

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.llm_gateway import LLMGateway, LLMMessage, LLMResponse
from app.models.student_profile import StudentProfile
from app.models.qa_record import QARecord
from app.prompts.qa_prompts import QA_SYSTEM_PROMPT
from loguru import logger


class QAAgent:
    """智能辅导 Agent"""

    def __init__(self):
        self.llm = LLMGateway()

    async def process(self, state: dict) -> dict:
        """处理问答"""
        user_id = state["user_id"]
        message = state["message"]

        # 获取画像摘要
        profile_summary = ""
        async with async_session_factory() as db:
            result = await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            if profile:
                pd = profile.profile_data
                profile_summary = (
                    f"知识水平: {pd.get('knowledge_base', {}).get('level', '未知')}\n"
                    f"认知风格: {pd.get('cognitive_style', {}).get('preference', '未知')}\n"
                    f"学习目标: {pd.get('learning_goals', {}).get('short_term', '未设置')}"
                )

        try:
            response = await self.llm.chat(
                messages=[LLMMessage("user", message)],
                system_prompt=QA_SYSTEM_PROMPT.format(profile_summary=profile_summary),
                temperature=0.7,
                max_tokens=2048,
            )

            return {
                "type": "qa_answer",
                "answer": response.content,
                "provider": response.provider,
            }
        except Exception as e:
            logger.error(f"QA Agent 错误: {e}")
            return {
                "type": "qa_error",
                "answer": f"抱歉，我遇到了一些问题：{str(e)}",
            }
