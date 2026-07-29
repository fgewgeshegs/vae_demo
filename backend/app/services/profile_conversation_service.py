"""对话式画像构建服务 - 通过自然语言对话自动构建学生画像"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from loguru import logger
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.llm_gateway import LLMGateway, LLMMessage
from app.models.student_profile import StudentProfile
from app.services.event_service import EventService, EventType
from app.services.student_state import StudentStateService


# 画像维度定义
PROFILE_DIMENSIONS = [
    "knowledge_base",
    "cognitive_style",
    "learning_goals",
    "knowledge_gaps",
    "learning_pace",
    "interest_direction",
    "weak_points",
    "learning_habits",  # 新增：学习习惯
    "motivation_factors",  # 新增：激励因素
]

# 画像模板
PROFILE_TEMPLATE: dict[str, Any] = {
    "knowledge_base": {"level": "beginner", "subjects": [], "foundation_score": 0},
    "cognitive_style": {"preference": "visual", "description": "", "processing_speed": "normal"},
    "learning_goals": {"short_term": "", "long_term": "", "milestones": []},
    "knowledge_gaps": [],
    "learning_pace": {"speed": "normal", "preferred_session_minutes": 30, "consistency": "regular"},
    "interest_direction": {"areas": [], "engagement_level": "medium"},
    "weak_points": [],
    "learning_habits": {
        "preferred_time": "unknown",
        "review_frequency": "unknown",
        "note_taking_style": "unknown",
    },
    "motivation_factors": {
        "intrinsic": [],
        "extrinsic": [],
        "reward_preference": "unknown",
    },
    "_meta": {"evidence": [], "conversation_history": [], "last_analysis": {}},
}

# 对话阶段定义
CONVERSATION_PHASES = {
    "initial": "初始了解阶段",
    "deepening": "深入探索阶段",
    "validation": "验证确认阶段",
    "completion": "完成阶段",
}

# 引导问题模板
GUIDING_QUESTIONS = {
    "knowledge_base": [
        "你目前在哪些学科或领域有学习经验？",
        "你觉得自己在哪些方面基础比较好？",
        "有没有哪些知识点你觉得需要加强？",
    ],
    "cognitive_style": [
        "你更喜欢通过看图表、听讲解还是动手实践来学习？",
        "学习新知识时，你通常采用什么方法？",
        "你觉得哪种学习方式对你最有效？",
    ],
    "learning_goals": [
        "你近期想达成什么学习目标？",
        "长期来看，你希望在哪些方面取得进步？",
        "有没有具体的学习里程碑想要实现？",
    ],
    "learning_pace": [
        "你通常一次能专注学习多长时间？",
        "你学习新内容的速度感觉如何？",
        "你更喜欢按自己的节奏学习还是有固定的时间表？",
    ],
    "interest_direction": [
        "你对哪些话题或领域特别感兴趣？",
        "有没有什么内容让你学起来特别有动力？",
        "你希望深入学习哪些方向？",
    ],
    "weak_points": [
        "你在学习中经常遇到哪些困难？",
        "有没有哪些类型的题目或概念总是出错？",
        "你觉得哪些方面需要更多的练习？",
    ],
    "learning_habits": [
        "你通常在什么时间段学习效果最好？",
        "你会定期复习学过的内容吗？",
        "你做笔记的习惯是怎样的？",
    ],
    "motivation_factors": [
        "什么会激励你坚持学习？",
        "你更看重内在的成长还是外在的认可？",
        "什么样的奖励方式对你最有效？",
    ],
}

# LLM对话提示词
CONVERSATION_SYSTEM_PROMPT = """你是一个专业的学习画像构建助手。你的任务是通过自然对话了解学生的学习情况，构建全面的学习画像。

对话原则：
1. 像朋友一样自然交流，不要像问卷调查
2. 每次只问1-2个问题，不要让学生感到压力
3. 根据学生的回答深入追问，获取更详细的信息
4. 适时给予积极反馈，鼓励学生分享
5. 从对话中自动提取画像信息，不需要学生明确说明
6. 保持对话的连贯性和逻辑性

当前阶段：{phase}
当前画像：{current_profile}

请根据对话历史和当前画像，生成下一步的对话内容。"""

# 画像提取提示词
PROFILE_EXTRACTION_PROMPT = """你是学习者画像分析专家。从对话内容中提取学习画像信息，要求覆盖以下6+个维度。

当前画像：
{current_profile}

对话内容：
{conversation}

## 画像维度定义

1. **knowledge_base（知识基础）**
   - level: beginner | intermediate | advanced（根据描述推断）
   - subjects: 熟悉或学习过的学科/技术领域列表
   - foundation_score: 基础评分 0-100（50=一般，80+=扎实）

2. **cognitive_style（认知风格）**
   - preference: visual | auditory | reading | kinesthetic | mixed
   - description: 具体的学习偏好描述
   - processing_speed: slow | normal | fast

3. **learning_goals（学习目标）**
   - short_term: 近期目标
   - long_term: 长期目标
   - milestones: 里程碑列表

4. **learning_pace（学习节奏）**
   - speed: slow | normal | fast
   - preferred_session_minutes: 单次学习时长（数字）
   - consistency: regular | irregular | sporadic

5. **interest_direction（兴趣方向）**
   - areas: 感兴趣的领域列表
   - engagement_level: low | medium | high

6. **weak_points + knowledge_gaps（薄弱环节）**
   - weak_points: 易错点
   - knowledge_gaps: 缺失的知识点

7. **learning_habits（学习习惯）** — 如有信息
   - preferred_time: morning | afternoon | evening | night | flexible
   - review_frequency: daily | weekly | rarely | never
   - note_taking_style: detailed | brief | visual | none

8. **motivation_factors（激励因素）** — 如有信息
   - intrinsic: 内在动力列表
   - extrinsic: 外在动力列表
   - reward_preference: verbal | tangible | achievement | social

## 推断规则

即使用户没有明确说明，也可以根据语境合理推断：
- "xx专业" → knowledge_base.subjects, level
- "喜欢/想学/对xx感兴趣" → interest_direction.areas
- "不太懂/不会/薄弱" → knowledge_gaps, weak_points
- "零基础/刚开始" → level=beginner
- "学了xx年" → level=intermediate 或 advanced
- "看视频/做项目" → cognitive_style.preference
- "每天/每周" → learning_pace.consistency
- "目标是/想要" → learning_goals

## 输出要求

1. 只输出 JSON，不要任何解释、Markdown 或代码块。
2. 只写有证据支持的字段，不要凭空捏造。
3. 空字符串、unknown、暂无、无、没有不要写入 updates。
4. 枚举值必须用英文小写。

## 输出格式

{{
  "updates": {{
    "knowledge_base": {{
      "level": "beginner|intermediate|advanced",
      "subjects": ["学科或技术"],
      "foundation_score": 60
    }},
    "cognitive_style": {{
      "preference": "visual|auditory|reading|kinesthetic|mixed",
      "description": "证据化描述",
      "processing_speed": "slow|normal|fast"
    }},
    "learning_goals": {{
      "short_term": "短期目标",
      "long_term": "长期目标",
      "milestones": ["里程碑"]
    }},
    "learning_pace": {{
      "speed": "slow|normal|fast",
      "preferred_session_minutes": 30,
      "consistency": "regular|irregular|sporadic"
    }},
    "interest_direction": {{
      "areas": ["兴趣领域"],
      "engagement_level": "low|medium|high"
    }},
    "knowledge_gaps": ["缺失的知识点"],
    "weak_points": ["易错点"],
    "learning_habits": {{
      "preferred_time": "morning|afternoon|evening|night|flexible",
      "review_frequency": "daily|weekly|rarely|never",
      "note_taking_style": "detailed|brief|visual|none"
    }},
    "motivation_factors": {{
      "intrinsic": ["内在动力"],
      "extrinsic": ["外在动力"],
      "reward_preference": "verbal|tangible|achievement|social"
    }}
  }},
  "evidence": [
    {{
      "field": "维度.字段",
      "quote": "用户原话中的证据",
      "confidence": 0.0到1.0
    }}
  ],
  "insufficient_evidence": ["没有足够证据的字段名"],
  "conversation_phase": "initial|deepening|validation|completion",
  "next_questions": ["基于当前画像缺失，建议的后续追问"]
}}

如果用户消息没有任何可提取的信息：
{{
  "updates": {{}},
  "evidence": [],
  "insufficient_evidence": [
    "knowledge_base.subjects",
    "interest_direction.areas",
    "cognitive_style.preference",
    "learning_goals.short_term",
    "weak_points"
  ],
  "conversation_phase": "current_phase",
  "next_questions": ["建议的后续问题"]
}}
"""


class ProfileConversationService:
    """对话式画像构建服务"""

    def __init__(self):
        self.llm = LLMGateway()
        self.student_state = StudentStateService()

    async def start_conversation(
        self, user_id: int, course_id: int | None = None
    ) -> dict[str, Any]:
        """开始新的画像构建对话"""
        # 加载当前画像
        profile = await self._load_profile(user_id)
        
        # 初始化对话状态
        conversation_state = {
            "user_id": user_id,
            "course_id": course_id,
            "phase": "initial",
            "history": [],
            "extracted_info": {},
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # 生成开场白
        opening_message = await self._generate_opening_message(profile, conversation_state)
        
        return {
            "type": "conversation_started",
            "conversation_id": f"profile_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
            "opening_message": opening_message,
            "current_profile": profile,
            "phase": "initial",
            "message": "画像构建对话已开始",
        }

    async def continue_conversation(
        self,
        user_id: int,
        conversation_id: str,
        message: str,
        course_id: int | None = None,
    ) -> dict[str, Any]:
        """继续对话并更新画像"""
        # 加载当前画像
        profile = await self._load_profile(user_id)
        
        # 分析用户消息，提取画像信息
        extraction_result = await self._extract_profile_info(profile, message)
        
        # 更新画像
        updated_profile = await self._update_profile(user_id, profile, extraction_result)
        
        # 生成回复
        response = await self._generate_response(
            updated_profile, extraction_result, message
        )
        
        return {
            "type": "conversation_continued",
            "conversation_id": conversation_id,
            "response": response,
            "updated_profile": updated_profile,
            "extraction_result": extraction_result,
            "message": "对话已继续，画像已更新",
        }

    async def end_conversation(
        self, user_id: int, conversation_id: str
    ) -> dict[str, Any]:
        """结束对话并生成最终画像"""
        profile = await self._load_profile(user_id)
        
        # 生成对话总结
        summary = await self._generate_conversation_summary(profile)
        
        return {
            "type": "conversation_ended",
            "conversation_id": conversation_id,
            "final_profile": profile,
            "summary": summary,
            "message": "画像构建对话已完成",
        }

    async def get_suggested_questions(
        self, user_id: int, profile: dict[str, Any]
    ) -> list[str]:
        """根据当前画像生成建议问题"""
        # 分析画像中信息不足的维度
        missing_dimensions = self._identify_missing_dimensions(profile)
        
        # 生成针对性问题
        questions = []
        for dimension in missing_dimensions[:3]:  # 最多3个维度
            if dimension in GUIDING_QUESTIONS:
                questions.extend(GUIDING_QUESTIONS[dimension][:2])
        
        return questions[:5]  # 最多5个问题

    async def _load_profile(self, user_id: int) -> dict[str, Any]:
        """加载用户画像"""
        async with async_session_factory() as db:
            result = await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                return deepcopy(PROFILE_TEMPLATE)
            
            return self._ensure_profile_shape(profile.profile_data)

    async def _extract_profile_info(
        self, current_profile: dict[str, Any], message: str
    ) -> dict[str, Any]:
        """从对话中提取画像信息"""
        try:
            # 构建对话上下文
            conversation_context = f"用户消息: {message}"
            
            # 调用LLM提取信息
            response = await self.llm.chat(
                messages=[
                    LLMMessage(
                        "user",
                        PROFILE_EXTRACTION_PROMPT.format(
                            current_profile=json.dumps(
                                current_profile, ensure_ascii=False
                            ),
                            conversation=conversation_context,
                        ),
                    )
                ],
                temperature=0.2,
                max_tokens=1500,
            )
            
            # 解析LLM响应
            raw = self._extract_json_object(response.content)
            return self._normalize_extraction_result(raw)
            
        except Exception as exc:
            logger.warning(f"Profile extraction failed: {exc}")
            return {
                "updates": {},
                "evidence": [],
                "insufficient_evidence": PROFILE_DIMENSIONS,
                "conversation_phase": "initial",
                "next_questions": [],
            }

    async def _update_profile(
        self,
        user_id: int,
        current_profile: dict[str, Any],
        extraction_result: dict[str, Any],
    ) -> dict[str, Any]:
        """更新用户画像"""
        updates = extraction_result.get("updates", {})
        evidence = extraction_result.get("evidence", [])
        
        if not updates:
            return current_profile
        
        # 合并更新
        next_profile = self._merge_updates(current_profile, updates)
        
        # 添加证据记录
        meta = next_profile.setdefault("_meta", {})
        evidence_log = meta.setdefault("evidence", [])
        now = datetime.now(timezone.utc).isoformat()
        for item in evidence:
            evidence_log.append({**item, "updated_at": now})
        meta["evidence"] = evidence_log[-50:]  # 保留最近50条证据
        
        # 保存到数据库
        await self._save_profile(user_id, next_profile)
        
        return next_profile

    async def _save_profile(self, user_id: int, profile_data: dict[str, Any]) -> None:
        """保存画像到数据库"""
        async with async_session_factory() as db:
            result = await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                profile = StudentProfile(
                    user_id=user_id,
                    profile_data=profile_data,
                )
                db.add(profile)
            else:
                profile.profile_data = profile_data
                profile.version += 1
            
            await db.flush()
            await db.commit()
            
            # 发送事件
            await EventService.emit(
                user_id=user_id,
                event_type=EventType.PROFILE_UPDATED,
                source_agent="ProfileConversationService",
                target_type="student_profile",
                target_id=profile.id,
                payload={
                    "version": profile.version,
                    "updated_fields": list(profile_data.keys()),
                },
            )

    async def _generate_opening_message(
        self, profile: dict[str, Any], conversation_state: dict[str, Any]
    ) -> str:
        """生成对话开场白"""
        # 分析当前画像状态
        missing = self._identify_missing_dimensions(profile)
        
        if not missing:
            return (
                "你好！我是你的学习画像助手。我已经了解到你的一些学习信息，"
                "如果你想更新或补充什么，随时告诉我！"
            )
        
        # 根据缺失维度生成开场白
        opening = "你好！我是你的学习画像助手。"
        
        if "knowledge_base" in missing:
            opening += "我想先了解一下你的学习基础，"
            opening += "你目前在哪些学科或领域有学习经验呢？"
        elif "cognitive_style" in missing:
            opening += "我想了解一下你的学习偏好，"
            opening += "你更喜欢通过什么方式学习新知识？"
        else:
            opening += "我想更全面地了解你的学习情况，"
            opening += "可以从你最想分享的方面开始聊聊。"
        
        return opening

    async def _generate_response(
        self,
        profile: dict[str, Any],
        extraction_result: dict[str, Any],
        user_message: str,
    ) -> str:
        """生成对话回复"""
        # 分析提取结果
        updated_fields = extraction_result.get("updates", {})
        insufficient = extraction_result.get("insufficient_evidence", [])
        next_questions = extraction_result.get("next_questions", [])
        
        # 构建回复
        response_parts = []
        
        # 确认信息已记录
        if updated_fields:
            response_parts.append("我已经记录了你分享的信息。")
        
        # 根据缺失信息生成后续问题
        if next_questions:
            response_parts.append(next_questions[0])
        elif insufficient:
            # 从预设问题中选择
            missing = self._identify_missing_dimensions(profile)
            if missing:
                dimension = missing[0]
                if dimension in GUIDING_QUESTIONS:
                    response_parts.append(GUIDING_QUESTIONS[dimension][0])
        
        # 如果没有其他内容，生成通用回复
        if not response_parts:
            response_parts.append("谢谢你的分享！还有什么想告诉我关于你的学习情况吗？")
        
        return " ".join(response_parts)

    async def _generate_conversation_summary(
        self, profile: dict[str, Any]
    ) -> dict[str, Any]:
        """生成对话总结"""
        return {
            "completed_dimensions": self._identify_completed_dimensions(profile),
            "missing_dimensions": self._identify_missing_dimensions(profile),
            "total_evidence": len(profile.get("_meta", {}).get("evidence", [])),
            "profile_completeness": self._calculate_completeness(profile),
        }

    def _identify_missing_dimensions(self, profile: dict[str, Any]) -> list[str]:
        """识别信息不足的维度"""
        missing = []
        
        for dimension in PROFILE_DIMENSIONS:
            if dimension not in profile:
                missing.append(dimension)
                continue
            
            value = profile[dimension]
            
            if isinstance(value, dict):
                # 检查字典是否为空或只有默认值
                if not value or all(
                    v in (None, "", [], {}, "unknown") for v in value.values()
                ):
                    missing.append(dimension)
            elif isinstance(value, list):
                if not value:
                    missing.append(dimension)
            elif value in (None, "", "unknown"):
                missing.append(dimension)
        
        return missing

    def _identify_completed_dimensions(self, profile: dict[str, Any]) -> list[str]:
        """识别信息完整的维度"""
        completed = []
        
        for dimension in PROFILE_DIMENSIONS:
            if dimension not in profile:
                continue
            
            value = profile[dimension]
            
            if isinstance(value, dict):
                if value and not all(
                    v in (None, "", [], {}, "unknown") for v in value.values()
                ):
                    completed.append(dimension)
            elif isinstance(value, list):
                if value:
                    completed.append(dimension)
            elif value and value not in ("unknown", ""):
                completed.append(dimension)
        
        return completed

    def _calculate_completeness(self, profile: dict[str, Any]) -> float:
        """计算画像完整度"""
        completed = len(self._identify_completed_dimensions(profile))
        total = len(PROFILE_DIMENSIONS)
        return round(completed / total * 100, 1) if total > 0 else 0.0

    def _ensure_profile_shape(self, data: dict[str, Any] | None) -> dict[str, Any]:
        """确保画像结构完整"""
        profile = deepcopy(PROFILE_TEMPLATE)
        if not isinstance(data, dict):
            return profile
        
        for key, value in data.items():
            if key in profile and isinstance(profile[key], dict) and isinstance(value, dict):
                profile[key].update(value)
            elif key in profile and isinstance(profile[key], list) and isinstance(value, list):
                profile[key] = value
            elif key == "_meta" and isinstance(value, dict):
                profile["_meta"].update(value)
            elif key in PROFILE_DIMENSIONS:
                profile[key] = value
        
        return profile

    def _extract_json_object(self, content: str) -> dict[str, Any]:
        """从LLM响应中提取JSON对象（健壮版本）"""
        text = (content or "").strip()
        if not text:
            raise ValueError("LLM returned empty content")

        # Strategy 1: Try fenced code block
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if fence_match:
            parsed = self._safe_parse_json(fence_match.group(1).strip())
            if parsed is not None:
                return parsed

        # Strategy 2: If the whole text is a JSON object
        if text.startswith("{"):
            parsed = self._safe_parse_json(text)
            if parsed is not None:
                return parsed

        # Strategy 3: Find all JSON objects in the text, prefer the one with "updates"
        candidates: list[dict[str, Any]] = []
        for match in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, flags=re.DOTALL):
            candidate_str = match.group(0)
            parsed = self._safe_parse_json(candidate_str)
            if parsed is not None:
                candidates.append(parsed)

        if candidates:
            # Prefer the candidate with "updates" key
            for c in candidates:
                if "updates" in c and isinstance(c["updates"], dict) and c["updates"]:
                    return c
            # Otherwise prefer the largest candidate
            best = max(candidates, key=lambda c: len(json.dumps(c, ensure_ascii=False)))
            if best:
                return best

        # Strategy 4: Try extracting between first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            parsed = self._safe_parse_json(text[start : end + 1])
            if parsed is not None:
                return parsed

        raise ValueError(
            f"No valid JSON object with profile data found in LLM response "
            f"(length={len(text)}, first 200 chars: {text[:200]!r})"
        )

    @staticmethod
    def _safe_parse_json(text: str) -> dict[str, Any] | None:
        """安全解析JSON，失败或结果为空时返回None"""
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None
        if not isinstance(parsed, dict):
            return None
        if not parsed:
            return None
        updates = parsed.get("updates")
        if "updates" in parsed and isinstance(updates, dict) and not updates:
            if "evidence" in parsed or "insufficient_evidence" in parsed:
                return parsed
            return None
        return parsed

    def _normalize_extraction_result(
        self, raw: dict[str, Any]
    ) -> dict[str, Any]:
        """规范化提取结果"""
        updates = raw.get("updates") if isinstance(raw.get("updates"), dict) else {}
        evidence = raw.get("evidence") if isinstance(raw.get("evidence"), list) else []
        insufficient = (
            raw.get("insufficient_evidence")
            if isinstance(raw.get("insufficient_evidence"), list)
            else []
        )
        phase = raw.get("conversation_phase", "initial")
        next_questions = (
            raw.get("next_questions")
            if isinstance(raw.get("next_questions"), list)
            else []
        )
        
        # 规范化更新内容
        normalized_updates = {}
        
        # 处理 knowledge_base
        knowledge_base = updates.get("knowledge_base")
        if isinstance(knowledge_base, dict):
            clean = {}
            level = knowledge_base.get("level")
            if level and level in ("beginner", "intermediate", "advanced"):
                clean["level"] = level
            subjects = knowledge_base.get("subjects")
            if isinstance(subjects, list):
                clean["subjects"] = [s for s in subjects if isinstance(s, str) and s.strip()]
            foundation_score = knowledge_base.get("foundation_score")
            if isinstance(foundation_score, (int, float)) and 0 <= foundation_score <= 100:
                clean["foundation_score"] = int(foundation_score)
            if clean:
                normalized_updates["knowledge_base"] = clean
        
        # 处理 cognitive_style
        cognitive_style = updates.get("cognitive_style")
        if isinstance(cognitive_style, dict):
            clean = {}
            preference = cognitive_style.get("preference")
            if preference and preference in (
                "visual", "auditory", "reading", "kinesthetic", "mixed"
            ):
                clean["preference"] = preference
            description = cognitive_style.get("description")
            if isinstance(description, str) and description.strip():
                clean["description"] = description.strip()
            processing_speed = cognitive_style.get("processing_speed")
            if processing_speed and processing_speed in ("slow", "normal", "fast"):
                clean["processing_speed"] = processing_speed
            if clean:
                normalized_updates["cognitive_style"] = clean
        
        # 处理 learning_goals
        learning_goals = updates.get("learning_goals")
        if isinstance(learning_goals, dict):
            clean = {}
            short_term = learning_goals.get("short_term")
            if isinstance(short_term, str) and short_term.strip():
                clean["short_term"] = short_term.strip()
            long_term = learning_goals.get("long_term")
            if isinstance(long_term, str) and long_term.strip():
                clean["long_term"] = long_term.strip()
            milestones = learning_goals.get("milestones")
            if isinstance(milestones, list):
                clean["milestones"] = [m for m in milestones if isinstance(m, str) and m.strip()]
            if clean:
                normalized_updates["learning_goals"] = clean
        
        # 处理 learning_pace
        learning_pace = updates.get("learning_pace")
        if isinstance(learning_pace, dict):
            clean = {}
            speed = learning_pace.get("speed")
            if speed and speed in ("slow", "normal", "fast"):
                clean["speed"] = speed
            minutes = learning_pace.get("preferred_session_minutes")
            if isinstance(minutes, int) and 5 <= minutes <= 240:
                clean["preferred_session_minutes"] = minutes
            consistency = learning_pace.get("consistency")
            if consistency and consistency in ("regular", "irregular", "sporadic"):
                clean["consistency"] = consistency
            if clean:
                normalized_updates["learning_pace"] = clean
        
        # 处理 interest_direction
        interest_direction = updates.get("interest_direction")
        if isinstance(interest_direction, dict):
            clean = {}
            areas = interest_direction.get("areas")
            if isinstance(areas, list):
                clean["areas"] = [a for a in areas if isinstance(a, str) and a.strip()]
            engagement_level = interest_direction.get("engagement_level")
            if engagement_level and engagement_level in ("low", "medium", "high"):
                clean["engagement_level"] = engagement_level
            if clean:
                normalized_updates["interest_direction"] = clean
        
        # 处理列表字段
        for list_key in ("knowledge_gaps", "weak_points"):
            values = updates.get(list_key)
            if isinstance(values, list):
                cleaned = [v for v in values if isinstance(v, str) and v.strip()]
                if cleaned:
                    normalized_updates[list_key] = cleaned
        
        # 处理 learning_habits
        learning_habits = updates.get("learning_habits")
        if isinstance(learning_habits, dict):
            clean = {}
            preferred_time = learning_habits.get("preferred_time")
            if preferred_time and preferred_time in (
                "morning", "afternoon", "evening", "night", "flexible"
            ):
                clean["preferred_time"] = preferred_time
            review_frequency = learning_habits.get("review_frequency")
            if review_frequency and review_frequency in ("daily", "weekly", "rarely", "never"):
                clean["review_frequency"] = review_frequency
            note_taking_style = learning_habits.get("note_taking_style")
            if note_taking_style and note_taking_style in ("detailed", "brief", "visual", "none"):
                clean["note_taking_style"] = note_taking_style
            if clean:
                normalized_updates["learning_habits"] = clean
        
        # 处理 motivation_factors
        motivation_factors = updates.get("motivation_factors")
        if isinstance(motivation_factors, dict):
            clean = {}
            intrinsic = motivation_factors.get("intrinsic")
            if isinstance(intrinsic, list):
                clean["intrinsic"] = [i for i in intrinsic if isinstance(i, str) and i.strip()]
            extrinsic = motivation_factors.get("extrinsic")
            if isinstance(extrinsic, list):
                clean["extrinsic"] = [e for e in extrinsic if isinstance(e, str) and e.strip()]
            reward_preference = motivation_factors.get("reward_preference")
            if reward_preference and reward_preference in (
                "verbal", "tangible", "achievement", "social"
            ):
                clean["reward_preference"] = reward_preference
            if clean:
                normalized_updates["motivation_factors"] = clean
        
        # 规范化证据
        clean_evidence = []
        for item in evidence:
            if not isinstance(item, dict):
                continue
            field = item.get("field")
            quote = item.get("quote")
            confidence = item.get("confidence")
            if not field or not quote:
                continue
            clean_item = {"field": str(field), "quote": str(quote)[:120]}
            if isinstance(confidence, (int, float)):
                clean_item["confidence"] = max(0, min(1, float(confidence)))
            clean_evidence.append(clean_item)
        
        # 规范化不足证据
        clean_insufficient = [
            item for item in insufficient if isinstance(item, str) and item.strip()
        ]
        
        # 规范化后续问题
        clean_next_questions = [
            q for q in next_questions if isinstance(q, str) and q.strip()
        ]
        
        return {
            "updates": normalized_updates,
            "evidence": clean_evidence,
            "insufficient_evidence": clean_insufficient,
            "conversation_phase": phase,
            "next_questions": clean_next_questions,
        }

    def _merge_updates(
        self, current: dict[str, Any], updates: dict[str, Any]
    ) -> dict[str, Any]:
        """合并更新到当前画像"""
        result = deepcopy(current)
        
        for key, value in updates.items():
            if key not in PROFILE_DIMENSIONS and key != "_meta":
                continue
            
            if isinstance(result.get(key), dict) and isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, list):
                        # 合并列表
                        existing = result[key].get(sub_key, [])
                        if isinstance(existing, list):
                            merged = list(dict.fromkeys([*existing, *sub_value]))
                            result[key][sub_key] = merged
                        else:
                            result[key][sub_key] = sub_value
                    else:
                        result[key][sub_key] = sub_value
            elif isinstance(result.get(key), list) and isinstance(value, list):
                # 合并列表
                existing = result.get(key, [])
                merged = list(dict.fromkeys([*existing, *value]))
                result[key] = merged
            else:
                result[key] = value
        
        return result


# 单例
profile_conversation_service = ProfileConversationService()
