"""系统配置 Pydantic Schemas"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class SystemConfigCreate(BaseModel):
    config_key: str = Field(..., max_length=100)
    config_value: str
    config_type: str = Field("string", pattern=r"^(string|json|number|boolean)$")
    description: str | None = None
    is_secret: bool = False


class SystemConfigResponse(BaseModel):
    id: int
    config_key: str
    config_value: str
    config_type: str
    description: str | None = None
    is_secret: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
