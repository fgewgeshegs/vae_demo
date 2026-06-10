"""应用配置管理"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "AI 个性化学习平台"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://ailearn:ailearn123@localhost:5432/ai_learning"

    # Redis
    REDIS_URL: str = "redis://:redispass@localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-this-to-a-random-secret-key-dev"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # LLM 供应商
    LLM_PROVIDER: str = "mock"

    # DeepSeek
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # GLM (智谱)
    GLM_API_KEY: Optional[str] = None
    GLM_API_BASE: str = "https://open.bigmodel.cn/api/paas/v4"
    GLM_MODEL: str = "glm-4"

    # Qwen (通义千问)
    QWEN_API_KEY: Optional[str] = None
    QWEN_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-plus"

    # Mock
    LLM_MOCK_DELAY: float = 0.5

    # 文件上传
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # 日志
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def upload_dir_path(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)


settings = Settings()

# 确保上传目录存在
settings.upload_dir_path
