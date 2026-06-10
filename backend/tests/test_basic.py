"""基础测试 - 验证核心模块可正常导入"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_imports():
    """验证关键模块可导入"""
    from app.core.config import settings
    assert settings.APP_NAME == "AI 个性化学习平台"

    from app.core.database import get_db, init_db, close_db
    import inspect
    assert inspect.iscoroutinefunction(init_db)
    assert inspect.iscoroutinefunction(close_db)

    from app.services.embedder import Embedder
    embedder = Embedder()
    assert embedder.dimension == 1536

    from app.core.llm_gateway import LLMGateway
    gateway = LLMGateway()
    assert gateway is not None

    from app.schemas.common import APIResponse
    resp = APIResponse(data={"test": "value"})
    assert resp.code == 200
    assert resp.data == {"test": "value"}
