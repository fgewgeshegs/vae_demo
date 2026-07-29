"""多供应商 LLM 接入网关 + Mock 模式

支持 DeepSeek / GLM / Qwen / OpenAI / Mock
"""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from enum import Enum
from typing import AsyncGenerator, Dict, List, Optional, Union

import httpx
from loguru import logger

from app.core.config import settings

_shared_http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=120.0))


@asynccontextmanager
async def _client_context():
    yield _shared_http_client


async def close_llm_http_client() -> None:
    await _shared_http_client.aclose()


class LLMProvider(str, Enum):
    MOCK = "mock"
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    GLM = "glm"
    QWEN = "qwen"


class LLMMessage:
    """对话消息"""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class LLMResponse:
    """LLM 响应"""

    def __init__(
        self,
        content: str,
        provider: str,
        model: str,
        usage: Optional[dict] = None,
        tool_calls: Optional[list[dict]] = None,
    ):
        self.content = content
        self.provider = provider
        self.model = model
        self.usage = usage or {}
        self.tool_calls = tool_calls or []


class LLMGateway:
    """LLM 网关 - 多供应商统一接口"""

    PROVIDER_CONFIGS = {
        LLMProvider.DEEPSEEK: {
            "api_key": settings.DEEPSEEK_API_KEY,
            "api_base": settings.DEEPSEEK_API_BASE,
            "model": settings.DEEPSEEK_MODEL,
        },
        LLMProvider.OPENAI: {
            "api_key": settings.OPENAI_API_KEY,
            "api_base": settings.OPENAI_API_BASE,
            "model": settings.OPENAI_MODEL,
        },
        LLMProvider.GLM: {
            "api_key": settings.GLM_API_KEY,
            "api_base": settings.GLM_API_BASE,
            "model": settings.GLM_MODEL,
        },
        LLMProvider.QWEN: {
            "api_key": settings.QWEN_API_KEY,
            "api_base": settings.QWEN_API_BASE,
            "model": settings.QWEN_MODEL,
        },
    }

    def __init__(self, provider: Optional[LLMProvider] = None):
        self._fixed_provider = provider
        provider_name = provider or settings.LLM_PROVIDER
        self.provider = LLMProvider(provider_name)
        self.config = self.PROVIDER_CONFIGS.get(self.provider, {})

    def _refresh_runtime_config(self) -> None:
        if self._fixed_provider is None:
            self.provider = LLMProvider(settings.LLM_PROVIDER)
        prefix = self.provider.value.upper()
        self.config = {
            "api_key": getattr(settings, f"{prefix}_API_KEY", None),
            "api_base": getattr(settings, f"{prefix}_API_BASE", ""),
            "model": getattr(settings, f"{prefix}_MODEL", ""),
        }

    async def chat(
        self,
        messages: List[Union[dict, LLMMessage]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str] = None,
    ) -> LLMResponse:
        """统一聊天接口"""
        # 转换为 dict
        self._refresh_runtime_config()
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        for m in messages:
            msgs.append(m.to_dict() if isinstance(m, LLMMessage) else m)

        if self.provider == LLMProvider.MOCK:
            return await self._mock_chat(msgs, temperature, max_tokens)

        return await self._openai_compatible_chat(
            msgs, temperature, max_tokens, stream, tools, tool_choice
        )

    async def _mock_chat(
        self,
        messages: list,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Mock 模式 - 返回模拟响应"""
        delay = settings.LLM_MOCK_DELAY
        await asyncio.sleep(delay)

        # 从最后一条消息提取关键词构造模拟回复
        last_msg = messages[-1]["content"] if messages else ""

        # 检测是否是结构化提取 prompt（如画像提取、评估生成等）
        content = self._mock_structured_response(last_msg)
        if content is None:
            content = (
                f"【Mock 回复】\n\n"
                f"我已收到你的消息：\n\n> {last_msg[:200]}\n\n"
                f"当前处于 Mock 模式，这是一个模拟回复。\n\n"
                f"请配置真实的 LLM API Key 以获取智能回复。\n"
                f"你可以在 /settings 页面配置 API Key 和模型。"
            )

        return LLMResponse(
            content=content,
            provider="mock",
            model="mock-model",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )

    @staticmethod
    def _mock_structured_response(prompt: str) -> str | None:
        """检测结构化提取 prompt，返回合理的模拟 JSON。"""
        # 画像提取 prompt 检测
        if "学习画像" in prompt and "updates" in prompt:
            import json
            return json.dumps({
                "updates": {
                    "knowledge_base": {
                        "level": "intermediate",
                        "subjects": ["计算机科学"],
                    },
                    "learning_goals": {
                        "short_term": "学习机器学习基础",
                    },
                    "interest_direction": {
                        "areas": ["人工智能", "机器学习"],
                    },
                    "weak_points": ["数学基础"],
                },
                "evidence": [
                    {
                        "field": "knowledge_base.subjects",
                        "quote": "计算机专业大三学生",
                        "confidence": 0.85,
                    },
                    {
                        "field": "learning_goals.short_term",
                        "quote": "想学习机器学习",
                        "confidence": 0.9,
                    },
                    {
                        "field": "weak_points",
                        "quote": "数学基础不太好",
                        "confidence": 0.8,
                    },
                ],
                "insufficient_evidence": [
                    "cognitive_style.preference",
                    "learning_pace.speed",
                ],
            }, ensure_ascii=False)

        # 评估生成 prompt 检测
        if "学习评估" in prompt or "评估报告" in prompt:
            import json
            return json.dumps({
                "scores": {"理解": 75, "应用": 60, "综合": 70},
                "suggestions": ["加强实践练习", "复习基础知识"],
                "strategy_signals": {"pace": "normal", "style": "visual"},
            }, ensure_ascii=False)

        return None

    async def _openai_compatible_chat(
        self,
        messages: list,
        temperature: float,
        max_tokens: int,
        stream: bool,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str] = None,
    ) -> LLMResponse:
        """兼容 OpenAI API 的聊天"""
        api_key = self.config.get("api_key")
        if not api_key:
            logger.warning(f"未配置 {self.provider.value} 的 API Key，回退到 Mock")
            return await self._mock_chat(messages, temperature, max_tokens)

        api_base = self.config["api_base"].rstrip("/")
        model = self.config["model"]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"

        async with _client_context() as client:
            try:
                response = await client.post(
                    f"{api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                message = data["choices"][0]["message"]
                content = message.get("content") or ""
                usage = data.get("usage", {})

                return LLMResponse(
                    content=content,
                    provider=self.provider.value,
                    model=model,
                    usage=usage,
                    tool_calls=message.get("tool_calls", []),
                )
            except Exception as e:
                logger.error(f"LLM 调用失败 ({self.provider.value}): {e}")
                raise

    async def chat_stream(
        self,
        messages: List[Union[dict, LLMMessage]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """流式聊天"""
        self._refresh_runtime_config()
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        for m in messages:
            msgs.append(m.to_dict() if isinstance(m, LLMMessage) else m)

        if self.provider == LLMProvider.MOCK:
            yield "【Mock 流式回复】\n\n当前为 Mock 模式，请配置 API Key。"
            return

        api_key = self.config.get("api_key")
        if not api_key:
            yield "【未配置 API Key】请先配置 LLM API Key。"
            return

        api_base = self.config["api_base"].rstrip("/")
        model = self.config["model"]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with _client_context() as client:
            async with client.stream(
                "POST", f"{api_base}/chat/completions", headers=headers, json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

    async def chat_stream_structured(
        self,
        messages: List[Union[dict, LLMMessage]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str] = None,
    ) -> AsyncGenerator[dict, None]:
        """结构化流式聊天 — yield {"type": "thinking"|"answer"|"tool_calls", "content": ...}

        V4 thinking mode: reasoning_content → thinking, content → answer
        """
        self._refresh_runtime_config()
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        for m in messages:
            msgs.append(m.to_dict() if isinstance(m, LLMMessage) else m)

        # Mock 模式
        if self.provider == LLMProvider.MOCK:
            yield {"type": "answer", "content": "【Mock 流式回复】\n\n当前为 Mock 模式，请配置 API Key。"}
            return

        api_key = self.config.get("api_key")
        if not api_key:
            yield {"type": "answer", "content": "【未配置 API Key】请先配置 LLM API Key。"}
            return

        api_base = self.config["api_base"].rstrip("/")
        model = self.config["model"]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload: dict = {
            "model": model,
            "messages": msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"

        collected_tool_calls: dict[int, dict] = {}

        async with _client_context() as client:
            async with client.stream(
                "POST", f"{api_base}/chat/completions", headers=headers, json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        choice = data["choices"][0]
                        delta = choice.get("delta", {})
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

                    # DeepSeek V4 thinking tokens
                    reasoning = delta.get("reasoning_content")
                    if reasoning:
                        yield {"type": "thinking", "content": reasoning}

                    # Normal answer content
                    content = delta.get("content")
                    if content:
                        yield {"type": "answer", "content": content}

                    # Tool call deltas (streamed incrementally)
                    for tc_delta in delta.get("tool_calls") or []:
                        idx = tc_delta.get("index", 0)
                        if idx not in collected_tool_calls:
                            collected_tool_calls[idx] = {
                                "id": tc_delta.get("id", ""),
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        tc = collected_tool_calls[idx]
                        fn = tc_delta.get("function", {})
                        if fn.get("name"):
                            tc["function"]["name"] = fn["name"]
                        if fn.get("arguments"):
                            tc["function"]["arguments"] += fn["arguments"]

                # After stream ends, emit collected tool calls
                if collected_tool_calls:
                    tool_calls = [collected_tool_calls[k] for k in sorted(collected_tool_calls)]
                    yield {"type": "tool_calls", "tool_calls": tool_calls}


# 单例
gateway = LLMGateway()


def get_llm_gateway() -> LLMGateway:
    """获取 LLM 网关（依赖注入）"""
    return gateway
