"""画像构建 Agent - 对话信息抽取 → 7维画像更新"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.llm_gateway import LLMGateway, LLMMessage
from app.models.student_profile import StudentProfile
from app.prompts.profile_prompts import PROFILE_EXTRACTION_PROMPT
from loguru import logger


PROFILE_DIMENSIONS = [
    "knowledge_base",     # 知识基础
    "cognitive_style",    # 认知风格
    "learning_goals",     # 学习目标
    "knowledge_gaps",     # 知识短板
    "learning_pace",      # 学习节奏
    "interest_direction", # 兴趣方向
    "weak_points",        # 易错点
]


class ProfileAgent:
    """画像构建 Agent"""

    def __init__(self):
        self.llm = LLMGateway()

    async def process(self, state: dict) -> dict:
        """处理画像更新"""
        user_id = state["user_id"]
        message = state["message"]

        async with async_session_factory() as db:
            # 获取当前画像
            result = await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                # 创建默认画像
                profile_data = {
                    dim: {} for dim in PROFILE_DIMENSIONS
                }
                profile_data["knowledge_gaps"] = []
                profile_data["weak_points"] = []
                profile = StudentProfile(
                    user_id=user_id,
                    profile_data=profile_data,
                )
                db.add(profile)
                await db.flush()

            # 调用 LLM 提取画像更新
            try:
                llm_response = await self.llm.chat(
                    messages=[LLMMessage("user", PROFILE_EXTRACTION_PROMPT.format(
                        current_profile=json.dumps(profile.profile_data, ensure_ascii=False),
                        message=message,
                    ))],
                    temperature=0.3,
                    max_tokens=1024,
                )

                # 解析返回的 JSON
                updates = json.loads(llm_response.content)

                # 增量更新（旧维度加权衰减）
                current = profile.profile_data
                for key, value in updates.items():
                    if key in current and isinstance(current[key], dict) and isinstance(value, dict):
                        # dict 类型合并更新
                        current[key].update(value)
                    elif key in current and isinstance(current[key], list) and isinstance(value, list):
                        # list 类型追加（去重）
                        existing = set(str(item) for item in current[key])
                        for item in value:
                            if str(item) not in existing:
                                current[key].append(item)
                    else:
                        current[key] = value

                profile.profile_data = current
                profile.version += 1
                await db.flush()

                logger.info(f"画像更新成功: user_id={user_id}, version={profile.version}")
                return {
                    "type": "profile_updated",
                    "profile": profile.profile_data,
                    "version": profile.version,
                }

            except Exception as e:
                logger.error(f"画像更新失败: {e}")
                return {
                    "type": "profile_error",
                    "error": str(e),
                    "profile": profile.profile_data,
                }
