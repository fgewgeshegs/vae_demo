"""通用 Pydantic Schemas"""

from __future__ import annotations

from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""
    code: int = 200
    message: str = "success"
    data: T | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
