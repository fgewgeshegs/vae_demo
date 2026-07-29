"""DeepSeek-led agent orchestrator with explicit learning tools."""

from __future__ import annotations

import json
import re
import traceback
from typing import Any, AsyncGenerator

from loguru import logger
from app.services.retrieval_errors import RetrievalUnavailableError

from app.core.llm_gateway import LLMGateway, LLMMessage
from app.services.content_guard import ContentGuard, GuardDecision
from app.services.retriever import Retriever
from app.services.student_state import StudentStateService


TOOL_LABELS = {
    "rag_search": "知识检索",
    "learner_context": "学习者画像",
    "profile_update": "画像更新",
    "path_plan": "路径规划",
    "resource_generate": "资源生成",
    "learning_evaluate": "学习评估",
}

TOOL_ICONS = {
    "rag_search": "📚",
    "learner_context": "🎓",
    "profile_update": "📝",
    "path_plan": "🧭",
    "resource_generate": "📄",
    "learning_evaluate": "📊",
}


SYSTEM_PROMPT = """你是个性化学习平台的主 Agent，大脑由 DeepSeek 提供。

你的职责：
1. 理解学生真实需求，并自主决定是否调用工具。
2. 课程事实、教材内容、概念解释必须优先调用 rag_search 查询知识库。
3. 需要了解学生现状时调用 learner_context。只有用户明确提供了新的个人信息并要求记录或更新时，才调用 profile_update。
4. 用户明确要求生成路径、生成资源或生成评估时，调用对应工具。
5. 闲聊、澄清问题或不需要平台数据的请求可以直接回答。
6. 工具完成后，简洁说明结果、下一步建议以及可前往的页面。
7. 不要声称执行了未调用的工具，不要编造知识库来源。
"""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "rag_search",
            "description": "使用 BGE-M3 和 reranker 查询课程知识库。解释课程概念、回答教材问题前应调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要查询的课程问题或概念"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 3, "default": 3},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "learner_context",
            "description": "只读获取学生当前画像、学习路径进度和最近评估。用于根据学生现状给建议，不会修改数据。",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "profile_update",
            "description": "根据学生明确提供的新信息更新画像。仅在用户要求记录、更新或分析其新描述时使用。",
            "parameters": {
                "type": "object",
                "properties": {"description": {"type": "string"}},
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "path_plan",
            "description": "根据画像、课程知识点和学习策略生成个性化学习路径。",
            "parameters": {
                "type": "object",
                "properties": {"request": {"type": "string"}},
                "required": ["request"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resource_generate",
            "description": "为指定主题生成讲义、思维导图、练习题、代码或其他学习资源。",
            "parameters": {
                "type": "object",
                "properties": {"request": {"type": "string"}},
                "required": ["request"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "learning_evaluate",
            "description": "分析学习行为、问答、路径和资源使用情况并生成学习评估。",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


class CoordinatorAgent:
    """Let DeepSeek plan tool use; keep deterministic routing only as fallback."""

    def __init__(self):
        self.llm = LLMGateway()
        self.retriever = Retriever()
        self.student_state = StudentStateService()

    async def _run_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        user_id: int,
        course_id: int | None,
        original_message: str,
    ) -> dict:
        state = {
            "user_id": user_id,
            "course_id": course_id,
            "message": original_message,
        }

        if name == "rag_search":
            query = str(arguments.get("query") or original_message)
            limit = min(max(int(arguments.get("limit", 3)), 1), 3)
            results = await self.retriever.retrieve(
                query, course_id=course_id, limit=limit, user_id=user_id
            )
            compact = []
            for item in results:
                compact.append({
                    "content": item.get("content", "")[:900],
                    "source": item.get("source", ""),
                    "locator": item.get("locator", ""),
                    "title": item.get("title", ""),
                    "score": item.get("score", 0),
                })
            return {"type": "rag", "query": query, "results": compact}

        if name == "learner_context":
            return await self.student_state.load_learner_context(user_id, course_id)

        if name == "profile_update":
            from app.agents.profile_agent import ProfileAgent
            state["message"] = str(arguments.get("description") or original_message)
            return await ProfileAgent().process(state)

        if name == "path_plan":
            from app.agents.path_agent import PathAgent
            state["message"] = str(arguments.get("request") or original_message)
            state["student_state"] = await self.student_state.load(user_id, course_id)
            return await PathAgent().process(state)

        if name == "resource_generate":
            from app.agents.resource_agent import ResourceCoordinator
            state["message"] = str(arguments.get("request") or original_message)
            state["student_state"] = await self.student_state.load(user_id, course_id)
            return await ResourceCoordinator().process(state)

        if name == "learning_evaluate":
            from app.agents.eval_agent import EvalAgent
            state["student_state"] = await self.student_state.load(user_id, course_id)
            return await EvalAgent().process(state)

        return {"type": "tool_error", "message": f"未知工具：{name}"}

    async def _deepseek_process(
        self,
        user_id: int,
        course_id: int | None,
        message: str,
    ) -> dict:
        # --- Content-safety guard: reject explicit harmful prompts ---
        prompt_guard = ContentGuard.check_prompt(message)
        if prompt_guard.decision == GuardDecision.REJECT:
            logger.warning(f"Coordinator blocked harmful prompt from user {user_id}")
            return {
                "type": "guard_blocked",
                "message": prompt_guard.safe_message,
                "answer": prompt_guard.safe_message,
                "provider": "guard",
                "tools_used": [],
                "tool_results": [],
                "guard_decision": GuardDecision.REJECT.value,
            }

        conversation: list[dict] = [{"role": "user", "content": message}]
        tools_used = []
        tool_results = []
        executed = set()
        executed_names = set()
        final = None

        # One planning call only. Tool agents already perform their own generation.
        for _ in range(1):
            response = await self.llm.chat(
                messages=conversation,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=1024,
                tools=TOOLS,
                tool_choice="auto",
            )
            final = response
            if not response.tool_calls:
                break

            conversation.append({
                "role": "assistant",
                "content": response.content or None,
                "tool_calls": response.tool_calls,
            })
            for call in response.tool_calls[:3]:
                function = call.get("function", {})
                name = function.get("name", "")
                raw_arguments = function.get("arguments") or "{}"
                signature = f"{name}:{raw_arguments}"
                try:
                    arguments = json.loads(raw_arguments)
                except json.JSONDecodeError:
                    arguments = {}

                if signature in executed or name in executed_names:
                    result = {"type": "tool_skipped", "message": f"{name} 已经执行，本轮无需重复调用。"}
                else:
                    executed.add(signature)
                    executed_names.add(name)
                    result = await self._run_tool(name, arguments, user_id, course_id, message)
                    tools_used.append(name)
                    tool_results.append(result)
                conversation.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", name),
                    "name": name,
                    "content": json.dumps(result, ensure_ascii=False, default=str)[:10000],
                })

        self_contained_tools = {
            "profile_update",
            "path_plan",
            "resource_generate",
            "learning_evaluate",
        }
        if tools_used and all(name in self_contained_tools for name in tools_used):
            primary = tool_results[-1]
            return {**primary, "tools_used": tools_used, "tool_results": tool_results}

        if final is None or final.tool_calls:
            final = await self.llm.chat(
                messages=conversation + [{
                    "role": "user",
                    "content": "请停止调用工具，根据已有结果直接给出最终答复。",
                }],
                system_prompt=SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=1024,
            )

        final_text = re.sub(
            r"<[^>]*DSML[^>]*tool_calls>.*",
            "",
            final.content or "",
            flags=re.DOTALL,
        ).strip()
        primary = tool_results[-1] if tool_results else {}
        return {
            **primary,
            "type": primary.get("type", "assistant"),
            "message": final_text or primary.get("message", "处理完成"),
            "answer": final_text or primary.get("answer", ""),
            "provider": final.provider,
            "tools_used": tools_used,
            "tool_results": tool_results,
        }


    async def _deepseek_stream(
        self,
        user_id: int,
        course_id: int | None,
        message: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Streaming version — yields SSE-compatible event dicts with real-time tokens."""
        # --- Content-safety guard ---
        prompt_guard = ContentGuard.check_prompt(message)
        if prompt_guard.decision == GuardDecision.REJECT:
            yield {
                "type": "guard_blocked",
                "content": prompt_guard.safe_message,
                "guard_decision": GuardDecision.REJECT.value,
            }
            return

        conversation: list[dict] = [{"role": "user", "content": message}]
        tools_used: list[str] = []
        tool_results: list[dict] = []
        executed: set[str] = set()
        executed_names: set[str] = set()

        # --- Thinking: analysis steps ---
        yield {
            "type": "thinking",
            "content": "正在分析你的问题...",
            "steps": [{"label": "分析问题", "status": "running"}],
        }

        # --- First LLM call (planning + streaming tokens) ---
        collected_tool_calls: list[dict] = []
        has_streamed_tokens = False

        try:
            async for event in self.llm.chat_stream_structured(
                messages=conversation,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=1024,
                tools=TOOLS,
                tool_choice="auto",
            ):
                if event["type"] == "thinking":
                    yield {"type": "thinking_delta", "content": event["content"]}
                elif event["type"] == "answer":
                    has_streamed_tokens = True
                    yield {"type": "answer_delta", "content": event["content"]}
                elif event["type"] == "tool_calls":
                    collected_tool_calls = event.get("tool_calls", [])
        except Exception as exc:
            logger.error(f"DeepSeek streaming failed: {exc}")
            yield {"type": "error", "content": f"分析失败：{str(exc)}"}
            return

        yield {
            "type": "thinking",
            "content": "分析完成",
            "steps": [{"label": "分析问题", "status": "done"}, {"label": "调用模型", "status": "done"}],
        }
        steps_done = [{"label": "分析问题", "status": "done"}, {"label": "调用模型", "status": "done"}]

        # --- No tool calls → direct answer (already streamed above) ---
        if not collected_tool_calls:
            if not has_streamed_tokens:
                yield {"type": "answer_delta", "content": "处理完成"}
            yield {"type": "done"}
            return

        # --- Execute tool calls ---
        conversation.append({
            "role": "assistant",
            "content": None,
            "tool_calls": collected_tool_calls,
        })

        for call in collected_tool_calls[:3]:
            function = call.get("function", {})
            name = function.get("name", "")
            raw_arguments = function.get("arguments") or "{}"
            signature = f"{name}:{raw_arguments}"
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                arguments = {}

            if signature in executed or name in executed_names:
                result = {"type": "tool_skipped", "message": f"{name} 已经执行，本轮无需重复调用。"}
            else:
                tool_label = TOOL_LABELS.get(name, name)
                tool_icon = TOOL_ICONS.get(name, "🔧")

                yield {
                    "type": "tool_start",
                    "tool": name,
                    "tool_label": tool_label,
                    "tool_icon": tool_icon,
                    "content": f"{tool_icon} 正在调用 {tool_label}...",
                    "steps": steps_done + [{"label": tool_label, "status": "running"}],
                }

                executed.add(signature)
                executed_names.add(name)
                try:
                    result = await self._run_tool(name, arguments, user_id, course_id, message)
                    tools_used.append(name)
                    tool_results.append(result)
                    yield {
                        "type": "tool_end",
                        "tool": name,
                        "tool_label": tool_label,
                        "tool_icon": tool_icon,
                        "status": "success",
                        "content": f"{tool_icon} {tool_label} 完成",
                        "steps": steps_done + [{"label": tool_label, "status": "done"}],
                    }
                    steps_done.append({"label": tool_label, "status": "done"})
                except Exception as exc:
                    logger.error(f"Tool {name} failed: {exc}")
                    yield {
                        "type": "tool_end",
                        "tool": name,
                        "tool_label": tool_label,
                        "tool_icon": tool_icon,
                        "status": "failed",
                        "content": f"{tool_icon} {tool_label} 失败：{str(exc)}",
                        "steps": steps_done + [{"label": tool_label, "status": "failed"}],
                    }
                    steps_done.append({"label": tool_label, "status": "failed"})

            conversation.append({
                "role": "tool",
                "tool_call_id": call.get("id", name),
                "name": name,
                "content": json.dumps(result, ensure_ascii=False, default=str)[:10000],
            })

        # --- Self-contained tools: return result directly ---
        self_contained_tools = {
            "profile_update", "path_plan", "resource_generate", "learning_evaluate",
        }
        if tools_used and all(name in self_contained_tools for name in tools_used):
            primary = tool_results[-1]
            final_text = primary.get("message", primary.get("answer", "处理完成"))
            yield {"type": "answer_delta", "content": final_text}
            yield {"type": "done"}
            return

        # --- Second LLM call: final answer (streaming) ---
        yield {
            "type": "thinking",
            "content": "正在生成最终回复...",
            "steps": steps_done + [{"label": "生成回复", "status": "running"}],
        }

        try:
            async for event in self.llm.chat_stream_structured(
                messages=conversation + [{
                    "role": "user",
                    "content": "请停止调用工具，根据已有结果直接给出最终答复。",
                }],
                system_prompt=SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=1024,
            ):
                if event["type"] == "thinking":
                    yield {"type": "thinking_delta", "content": event["content"]}
                elif event["type"] == "answer":
                    yield {"type": "answer_delta", "content": event["content"]}
        except Exception as exc:
            logger.error(f"Final streaming call failed: {exc}")
            yield {"type": "error", "content": f"生成回复失败：{str(exc)}"}
            return

        yield {
            "type": "thinking",
            "content": "回复完成",
            "steps": steps_done + [{"label": "生成回复", "status": "done"}],
        }
        yield {"type": "done"}

    async def stream(
        self,
        user_id: int,
        course_id: int | None,
        message: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Public streaming entry point. Yields SSE-compatible event dicts."""
        try:
            async for event in self._deepseek_stream(user_id, course_id, message):
                yield event
        except Exception as exc:
            logger.error(f"Coordinator stream failed: {exc}\n{traceback.format_exc()}")
            yield {"type": "error", "content": f"系统错误：{str(exc)}"}


    async def _fallback_process(
        self,
        user_id: int,
        course_id: int | None,
        message: str,
    ) -> dict:
        """Keep the platform usable when DeepSeek planning is unavailable."""
        text = message.lower()
        state = {"user_id": user_id, "course_id": course_id, "message": message}
        if any(word in text for word in ["画像", "分析我", "学习目标"]):
            from app.agents.profile_agent import ProfileAgent
            return await ProfileAgent().process(state)
        if any(word in text for word in ["学习路径", "学习计划", "学习路线"]):
            from app.agents.path_agent import PathAgent
            return await PathAgent().process(state)
        if any(word in text for word in ["生成资源", "讲义", "思维导图", "练习题", "代码案例"]):
            from app.agents.resource_agent import ResourceCoordinator
            return await ResourceCoordinator().process(state)
        if any(word in text for word in ["评估", "学习报告", "学习效果"]):
            from app.agents.eval_agent import EvalAgent
            return await EvalAgent().process(state)
        from app.agents.qa_agent import QAAgent
        return await QAAgent().process(state)

    async def process(self, user_id: int, course_id: int | None, message: str) -> dict:
        try:
            result = await self._deepseek_process(user_id, course_id, message)
            logger.info(f"DeepSeek tools used: {result.get('tools_used', [])}")
            return result
        except Exception as exc:
            if isinstance(exc, RetrievalUnavailableError):
                raise
            logger.warning(f"DeepSeek orchestrator failed, using fallback: {exc}")
            return await self._fallback_process(user_id, course_id, message)


coordinator = CoordinatorAgent()


async def get_coordinator() -> CoordinatorAgent:
    return coordinator
