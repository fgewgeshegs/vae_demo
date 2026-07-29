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
    RETRIEVAL_CACHE_TTL_SECONDS: int = 300
    DOCUMENT_TASK_MAX_RETRIES: int = 3

    # JWT
    JWT_SECRET_KEY: str = "change-this-to-a-random-secret-key-dev"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    ADMIN_USERNAMES: str = "admin"

    # LLM 供应商
    LLM_PROVIDER: str = "mock"

    # DeepSeek
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"

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

    # Agnes Video API
    AGNES_API_KEY: Optional[str] = None
    AGNES_API_BASE: str = "https://apihub.agnes-ai.com"

    # 文件上传
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # 日志
    LOG_LEVEL: str = "INFO"
    SEED_RESOURCES_ON_STARTUP: bool = False

    # Local BGE retrieval
    BGE_MODEL_PATH: str = r"D:\jay_demo\models\bge-m3"
    BGE_RERANKER_PATH: str = r"D:\jay_demo\models\bge-reranker-v2-m3"
    BGE_DEVICE: str = "cuda"
    BGE_EMBEDDING_DIMENSION: int = 1024
    BGE_RETRIEVAL_CANDIDATES: int = 20
    BGE_RERANK_TOP_K: int = 5
    BGE_MAX_CONCURRENCY: int = 1
    BGE_QUEUE_TIMEOUT_SECONDS: float = 3.0
    BGE_INFERENCE_SERVICE_URL: Optional[str] = None
    BGE_INFERENCE_TIMEOUT_SECONDS: float = 30.0
    DOCUMENT_EMBED_BATCH_SIZE: int = 32
    MAX_CHUNK_SIZE: int = 500
    ANALYTICS_LOOKBACK_DAYS: int = 90
    HEALTH_CHECK_TIMEOUT_SECONDS: float = 15.0

    # SMTP 邮件
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "知境"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False

    @property
    def smtp_configured(self) -> bool:
        return bool(self.SMTP_HOST and self.SMTP_USERNAME and self.SMTP_PASSWORD)


    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def upload_dir_path(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def admin_usernames(self) -> set[str]:
        return {name.strip().lower() for name in self.ADMIN_USERNAMES.split(",") if name.strip()}

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)


settings = Settings()


def apply_runtime_config(key: str, value: str) -> bool:
    attribute = key.upper()
    if not hasattr(settings, attribute):
        return False
    current = getattr(settings, attribute)
    if isinstance(current, bool):
        parsed = value.strip().lower() in {"1", "true", "yes", "on"}
    elif isinstance(current, int):
        parsed = int(value)
    elif isinstance(current, float):
        parsed = float(value)
    else:
        parsed = value
    setattr(settings, attribute, parsed)
    return True

# 确保上传目录存在
settings.upload_dir_path
