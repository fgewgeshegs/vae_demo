"""多供应商 LLM 接入网关 + Mock 模式

支持 DeepSeek / GLM / Qwen / OpenAI / Mock
"""

from __future__ import annotations

import asyncio
import json
import time
from enum import Enum
from typing import AsyncGenerator, Dict, List, Optional, Union

import httpx
from loguru import logger

from app.core.config import settings


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

    def __init__(self, content: str, provider: str, model: str, usage: Optional[dict] = None):
        self.content = content
        self.provider = provider
        self.model = model
        self.usage = usage or {}


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
        provider_name = provider or settings.LLM_PROVIDER
        self.provider = LLMProvider(provider_name)
        self.config = self.PROVIDER_CONFIGS.get(self.provider, {})

    async def chat(
        self,
        messages: List[Union[dict, LLMMessage]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> LLMResponse:
        """统一聊天接口"""
        # 转换为 dict
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        for m in messages:
            msgs.append(m.to_dict() if isinstance(m, LLMMessage) else m)

        if self.provider == LLMProvider.MOCK:
            return await self._mock_chat(msgs, temperature, max_tokens)

        return await self._openai_compatible_chat(msgs, temperature, max_tokens, stream)

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

    async def _openai_compatible_chat(
        self,
        messages: list,
        temperature: float,
        max_tokens: int,
        stream: bool,
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

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})

                return LLMResponse(
                    content=content,
                    provider=self.provider.value,
                    model=model,
                    usage=usage,
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

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", f"{api_base}/chat/completions", headers=headers, json=payload
            ) as response:
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


# 单例
gateway = LLMGateway()


def get_llm_gateway() -> LLMGateway:
    """获取 LLM 网关（依赖注入）"""
    return gateway
