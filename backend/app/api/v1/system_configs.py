"""系统设置 API（运行时配置热替换）"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.system_config import SystemConfig
from app.schemas.system_config import SystemConfigCreate, SystemConfigResponse

router = APIRouter()


@router.get("/", response_model=list[SystemConfigResponse])
async def list_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有配置"""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.is_active == True).order_by(SystemConfig.config_key)
    )
    configs = result.scalars().all()

    # 隐藏 secret 类型配置的值
    resp = []
    for c in configs:
        r = SystemConfigResponse.model_validate(c)
        if c.is_secret and r.config_value:
            r.config_value = "********"
        resp.append(r)
    return resp


@router.put("/{config_key}", response_model=SystemConfigResponse)
async def update_config(
    config_key: str,
    data: SystemConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新配置（热生效）"""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == config_key)
    )
    config = result.scalar_one_or_none()

    if config:
        config.config_value = data.config_value
        if data.description:
            config.description = data.description
    else:
        config = SystemConfig(**data.model_dump())
        db.add(config)

    await db.flush()
    await db.commit()
    await db.refresh(config)
    return SystemConfigResponse.model_validate(config)


@router.get("/{config_key}", response_model=SystemConfigResponse)
async def get_config(
    config_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取配置项"""
    result = await db.execute(
        select(SystemConfig).where(
            SystemConfig.config_key == config_key,
            SystemConfig.is_active == True,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置项不存在")

    resp = SystemConfigResponse.model_validate(config)
    if config.is_secret and resp.config_value:
        resp.config_value = "********"
    return resp
