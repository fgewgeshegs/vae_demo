"""文本向量嵌入服务

支持真实 Embedding API（OpenAI / 兼容端点）和 Mock 回退。
"""

from __future__ import annotations

from typing import List, Optional

import httpx
from loguru import logger

from app.core.config import settings


class Embedder:
    """向量嵌入服务"""

    def __init__(self):
        self.model_name = "text-embedding-3-small"
        self.dimension = 1536

    def _get_active_config(self) -> Optional[dict]:
        """获取当前提供商的嵌入配置"""
        provider = settings.LLM_PROVIDER
        config_map = {
            "openai": {
                "api_key": settings.OPENAI_API_KEY,
                "api_base": settings.OPENAI_API_BASE,
                "model": "text-embedding-3-small",
            },
            "deepseek": {
                "api_key": settings.DEEPSEEK_API_KEY,
                "api_base": settings.DEEPSEEK_API_BASE,
                "model": "text-embedding-3-small",
            },
            "qwen": {
                "api_key": settings.QWEN_API_KEY,
                "api_base": settings.QWEN_API_BASE,
                "model": "text-embedding-v3",
            },
            "glm": {
                "api_key": settings.GLM_API_KEY,
                "api_base": settings.GLM_API_BASE,
                "model": "embedding-2",
            },
        }
        cfg = config_map.get(provider)
        if cfg and cfg.get("api_key"):
            return cfg
        return None

    async def embed(self, text: str) -> List[float]:
        """生成文本向量"""
        config = self._get_active_config()
        if config is None:
            logger.warning("未配置 Embedding API Key，返回零向量占位（功能受限）")
            return [0.0] * self.dimension

        api_base = config["api_base"].rstrip("/")
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config["model"],
            "input": text,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{api_base}/embeddings",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Embedding API 调用失败: {e}")
            return [0.0] * self.dimension

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成向量"""
        results = []
        for t in texts:
            results.append(await self.embed(t))
        return results
