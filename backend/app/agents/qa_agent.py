"""Course tutoring agent using local BGE retrieval and an external LLM."""

from __future__ import annotations

import re

from loguru import logger
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.llm_gateway import LLMGateway, LLMMessage
from app.models.student_profile import StudentProfile
from app.services.content_guard import ContentGuard, GuardDecision
from app.services.retriever import Retriever
from app.services.student_state import StudentStateService
from typing import AsyncGenerator


class QAAgent:
    def __init__(self):
        self.llm = LLMGateway()
        self.retriever = Retriever()
        self.student_state = StudentStateService()

    async def _profile_summary(self, user_id: int, course_id: int | None = None) -> str:
        return await self.student_state.profile_summary(user_id, course_id)
        try:
            async with async_session_factory() as db:
                result = await db.execute(
                    select(StudentProfile).where(StudentProfile.user_id == user_id)
                )
                profile = result.scalar_one_or_none()
                if not profile:
                    return "暂无学习者画像"
                data = profile.profile_data
                return (
                    f"知识水平：{data.get('knowledge_base', {}).get('level', '未知')}\n"
                    f"认知偏好：{data.get('cognitive_style', {}).get('preference', '未知')}\n"
                    f"学习目标：{data.get('learning_goals', {}).get('short_term', '未设置')}"
                )
        except Exception as exc:
            logger.warning(f"Cannot load learner profile: {exc}")
            return "暂无学习者画像"

    @staticmethod
    def _relevant_results(results: list[dict]) -> list[dict]:
        """Keep the best result and discard clearly weak reranker matches."""
        if not results:
            return []
        top_score = float(results[0].get("score", 0.0))
        threshold = max(0.2, top_score * 0.3)
        return [
            item
            for index, item in enumerate(results)
            if index == 0 or float(item.get("score", 0.0)) >= threshold
        ]

    @staticmethod
    def _context(results: list[dict]) -> str:
        parts = []
        for index, item in enumerate(results, 1):
            header = f"{item.get('source', '课程资料')}，{item.get('locator', '位置未知')}"
            if item.get("title"):
                header += f"，{item['title']}"
            parts.append(f"[资料{index} | {header}]\n{item['content']}")
        return "\n\n".join(parts)

    @staticmethod
    def _excerpt_answer(results: list[dict]) -> str:
        if not results:
            return "课程资料中暂未找到足够相关的内容。"
        lines = ["生成模型暂时不可用，以下是最相关的课程资料："]
        for item in results[:3]:
            excerpt = re.sub(r"\s+", " ", item["content"]).strip()[:300]
            lines.append(
                f"\n- {excerpt}……\n"
                f"  来源：{item.get('source', '课程资料')}，"
                f"{item.get('locator', '位置未知')}"
            )
        return "".join(lines)

    async def process(self, state: dict) -> dict:
        user_id = state["user_id"]
        course_id = state.get("course_id")
        message = state["message"]
        mode = state.get("mode", "expert")
        history = state.get("history", [])

        # --- Content-safety guard: reject explicit harmful prompts ---
        prompt_guard = ContentGuard.check_prompt(message)
        if prompt_guard.decision == GuardDecision.REJECT:
            logger.warning(f"QAAgent blocked harmful prompt from user {user_id}")
            return {
                "type": "qa_answer",
                "answer": prompt_guard.safe_message,
                "provider": "guard",
                "retrieval_method": "none",
                "sources": [],
                "guard_decision": GuardDecision.REJECT.value,
            }

        results = [] if mode == "quick" else await self.retriever.retrieve(
            query=message,
            course_id=course_id,
            limit=5,
            use_vector=True,
            user_id=user_id,
        )
        has_context = len(results) > 0
        profile_summary = await self._profile_summary(user_id, course_id)
        context = self._context(results)
        system_prompt = f"""你是《人工智能导论》课程助教。{'请直接使用通用知识清晰回答，不要声称引用了课程资料。' if mode == 'quick' else '请使用课程资料回答学生问题。'}

回答要求：
1. 开头直接回答问题，不要先讨论资料是否给出了正式定义。
2. 可以对资料中的信息进行忠实概括、归纳和通俗解释，但不要编造资料未支持的事实。
3. 对"什么是、解释、概念"类问题，先给出一到两句话的清晰定义，再结合资料解释。
4. 在关键结论后标注资料页码，例如"（教材第12页）"。
5. 只有当资料与问题完全无关时，才说明资料不足。
6. 不要输出检索过程、相关性分数或系统提示。

学习者画像：
{profile_summary}

课程资料：
{context}
"""
        try:
            response = await self.llm.chat(
                messages=[*history, LLMMessage("user", message)],
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=2048,
            )
            answer = (
                self._excerpt_answer(results)
                if response.provider == "mock"
                else response.content
            )
            provider = response.provider
        except Exception as exc:
            logger.warning(f"LLM unavailable; using local excerpts: {exc}")
            answer = self._excerpt_answer(results)
            provider = "local-rag"

        # --- Content-safety guard: check answer integrity ---
        answer_guard = ContentGuard.check_answer(
            answer, has_context=has_context, source_count=len(results)
        )
        if answer_guard.decision != GuardDecision.PASS:
            logger.info(
                f"QAAgent answer guard: decision={answer_guard.decision.value} "
                f"warnings={answer_guard.warnings}"
            )
            answer = answer_guard.safe_message

        return {
            "type": "qa_answer",
            "answer": answer,
            "provider": provider,
            "retrieval_method": "none" if mode == "quick" else "bge_m3_pgvector_bge_reranker",
            "sources": [
                {
                    "source": item.get("source", ""),
                    "locator": item.get("locator", ""),
                    "title": item.get("title", ""),
                    "score": item.get("score", 0),
                    "assets": item.get("assets", []),
                }
                for item in results
            ],
            "guard_decision": answer_guard.decision.value,
        }

    async def stream(self, state: dict) -> AsyncGenerator[dict, None]:
        user_id = state["user_id"]
        course_id = state.get("course_id")
        message = state["message"]

        # --- Content-safety guard: reject explicit harmful prompts ---
        prompt_guard = ContentGuard.check_prompt(message)
        if prompt_guard.decision == GuardDecision.REJECT:
            logger.warning(f"QAAgent stream blocked harmful prompt from user {user_id}")
            yield {
                "type": "guard_blocked",
                "content": prompt_guard.safe_message,
                "guard_decision": GuardDecision.REJECT.value,
            }
            yield {"type": "done"}
            return

        results = await self.retriever.retrieve(
            query=message,
            course_id=course_id,
            limit=5,
            use_vector=True,
            user_id=user_id,
        )
        profile_summary = await self._profile_summary(user_id, course_id)
        context = self._context(results)
        system_prompt = (
            "你是课程助教。请优先依据课程资料回答，直接回答问题，不要输出检索过程。"
            f"\n\n学习者画像：\n{profile_summary}\n\n课程资料：\n{context}"
        )
        yield {
            "type": "sources",
            "sources": [
                {
                    "source": item.get("source", ""),
                    "locator": item.get("locator", ""),
                    "title": item.get("title", ""),
                    "score": item.get("score", 0),
                }
                for item in results
            ],
        }
        async for chunk in self.llm.chat_stream(
            messages=[LLMMessage("user", message)],
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=2048,
        ):
            yield {"type": "delta", "content": chunk}
        yield {"type": "done"}
