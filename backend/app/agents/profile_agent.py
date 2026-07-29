"""Learner profile Agent: extract, validate, and persist structured profile data."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.llm_gateway import LLMGateway, LLMMessage
from app.models.student_profile import StudentProfile
from app.prompts.profile_prompts import PROFILE_EXTRACTION_PROMPT
from app.services.event_service import EventService, EventType


PROFILE_DIMENSIONS = [
    "knowledge_base",
    "cognitive_style",
    "learning_goals",
    "knowledge_gaps",
    "learning_pace",
    "interest_direction",
    "weak_points",
]

PROFILE_TEMPLATE: dict[str, Any] = {
    "knowledge_base": {"level": "beginner", "subjects": []},
    "cognitive_style": {"preference": "visual", "description": ""},
    "learning_goals": {"short_term": "", "long_term": ""},
    "knowledge_gaps": [],
    "learning_pace": {"speed": "normal", "preferred_session_minutes": 30},
    "interest_direction": {"areas": []},
    "weak_points": [],
    "_meta": {"evidence": [], "last_analysis": {}},
}

ALLOWED_LEVELS = {"beginner", "intermediate", "advanced"}
ALLOWED_PREFERENCES = {"visual", "auditory", "reading", "kinesthetic", "mixed"}
ALLOWED_SPEEDS = {"slow", "normal", "fast"}

LEVEL_ALIASES = {
    "beginner": "beginner",
    "入门": "beginner",
    "初学": "beginner",
    "新手": "beginner",
    "零基础": "beginner",
    "基础": "beginner",
    "intermediate": "intermediate",
    "中级": "intermediate",
    "中等": "intermediate",
    "进阶": "intermediate",
    "advanced": "advanced",
    "高级": "advanced",
    "熟练": "advanced",
    "专家": "advanced",
}

PREFERENCE_ALIASES = {
    "visual": "visual",
    "视觉": "visual",
    "图": "visual",
    "图像": "visual",
    "图解": "visual",
    "auditory": "auditory",
    "听觉": "auditory",
    "音频": "auditory",
    "听课": "auditory",
    "reading": "reading",
    "阅读": "reading",
    "文字": "reading",
    "文档": "reading",
    "kinesthetic": "kinesthetic",
    "实践": "kinesthetic",
    "动手": "kinesthetic",
    "实操": "kinesthetic",
    "项目": "kinesthetic",
    "mixed": "mixed",
    "混合": "mixed",
    "综合": "mixed",
}

SPEED_ALIASES = {
    "slow": "slow",
    "慢": "slow",
    "慢速": "slow",
    "normal": "normal",
    "正常": "normal",
    "适中": "normal",
    "中等": "normal",
    "fast": "fast",
    "快": "fast",
    "快速": "fast",
}

RULE_PATTERNS = [
    ("knowledge_subjects", r"(?:我的)?(?:知识)?基础(?:是|:|：)\s*([^\n。；;]+)"),
    ("knowledge_subjects", r"(?:我)?(?:熟悉|掌握|会)(?:的)?(?:领域|内容|知识)?(?:是|有|:|：)?\s*([^\n。；;]+)"),
    ("knowledge_gaps", r"(?:我)?(?:不熟悉|不会|不懂|薄弱|弱点|短板)(?:的)?(?:领域|内容|知识|点)?(?:是|有|:|：)?\s*([^\n。；;]+)"),
    ("short_goal", r"(?:短期目标|近期目标|现在想|我想先|目标)(?:是|:|：)\s*([^\n。；;]+)"),
    ("long_goal", r"(?:长期目标|最终目标|以后想|长期想)(?:是|:|：)\s*([^\n。；;]+)"),
    ("interest", r"(?:兴趣方向|感兴趣的领域|感兴趣|我喜欢)(?:是|有|:|：)?\s*([^\n。；;]+)"),
    ("preference", r"(?:学习方式|学习偏好|认知风格|偏好)(?:是|有|:|：)?\s*([^\n。；;]+)"),
    ("pace", r"(?:学习节奏|学习速度|进度)(?:是|偏|:|：)?\s*([^\n。；;]+)"),
]


class ProfileAgent:
    """Build and update a learner profile from explicit conversation evidence."""

    def __init__(self):
        self.llm = LLMGateway()

    async def process(self, state: dict) -> dict:
        user_id = state["user_id"]
        message = str(state.get("message") or "")

        async with async_session_factory() as db:
            result = await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                profile = StudentProfile(
                    user_id=user_id,
                    profile_data=self._default_profile(),
                )
                db.add(profile)
                await db.flush()
            else:
                profile.profile_data = self._ensure_profile_shape(profile.profile_data)

            rule_updates, rule_evidence = self._extract_rule_updates(message)
            llm_updates: dict[str, Any] = {}
            llm_evidence: list[dict[str, Any]] = []
            insufficient: list[str] = []
            llm_error = ""
            llm_preview = ""

            try:
                llm_response = await self.llm.chat(
                    messages=[
                        LLMMessage(
                            "user",
                            PROFILE_EXTRACTION_PROMPT.format(
                                current_profile=json.dumps(
                                    profile.profile_data,
                                    ensure_ascii=False,
                                ),
                                message=message,
                            ),
                        )
                    ],
                    temperature=0.2,
                    max_tokens=1200,
                )
                llm_preview = (llm_response.content or "")[:500]
                raw = self._extract_json_object(llm_response.content)
                llm_updates, llm_evidence, insufficient = self._normalize_updates(raw)
            except Exception as exc:
                llm_error = str(exc)
                logger.warning("Profile LLM extraction failed, using rule fallback: {}", exc)

            try:
                updates = self._merge_update_dicts(rule_updates, llm_updates)
                evidence = [*rule_evidence, *llm_evidence]
                current = self._ensure_profile_shape(profile.profile_data)
                next_profile, updated_fields = self._apply_updates(
                    current,
                    updates,
                    evidence,
                    insufficient,
                )

                if updated_fields:
                    # JSONB does not reliably notice nested in-place mutation.
                    profile.profile_data = next_profile
                    profile.version += 1

                await db.flush()
                await db.commit()
                await db.refresh(profile)

                if updated_fields:
                    await EventService.emit(
                        user_id=user_id,
                        course_id=state.get("course_id"),
                        event_type=EventType.PROFILE_UPDATED,
                        source_agent="ProfileAgent",
                        target_type="student_profile",
                        target_id=profile.id,
                        payload={
                            "version": profile.version,
                            "updated_fields": updated_fields,
                        },
                    )

                logger.info(
                    "Profile analysis completed: user_id={}, version={}, updated_fields={}",
                    user_id,
                    profile.version,
                    updated_fields,
                )

                if llm_error and not updated_fields:
                    message_text = "画像分析失败：模型没有返回可解析的结构化结果，且规则兜底也没有找到明确证据"
                elif updated_fields:
                    message_text = "画像已根据明确证据更新"
                else:
                    message_text = "画像已分析，但没有找到足够明确的新证据"

                return {
                    "type": "profile_updated",
                    "profile": profile.profile_data,
                    "version": profile.version,
                    "updated_fields": updated_fields,
                    "insufficient_evidence": insufficient,
                    "evidence": evidence,
                    "message": message_text,
                    "debug": {
                        "llm_error": llm_error,
                        "llm_output_preview": llm_preview,
                        "rule_updates": rule_updates,
                        "llm_updates": llm_updates,
                    },
                }
            except Exception as exc:
                logger.error("Profile analysis failed: {}", exc)
                return {
                    "type": "profile_error",
                    "error": str(exc),
                    "profile": profile.profile_data,
                }

    def _default_profile(self) -> dict[str, Any]:
        return deepcopy(PROFILE_TEMPLATE)

    def _ensure_profile_shape(self, data: dict[str, Any] | None) -> dict[str, Any]:
        profile = self._default_profile()
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
        """Parse JSON safely, returning None on failure or empty/trivial results."""
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None
        if not isinstance(parsed, dict):
            return None
        # Skip trivially empty objects or objects with empty "updates"
        if not parsed:
            return None
        updates = parsed.get("updates")
        if "updates" in parsed and isinstance(updates, dict) and not updates:
            # Has "updates" key but it's empty - still valid for "no updates" case,
            # but only return if it also has evidence/insufficient keys (structured output)
            if "evidence" in parsed or "insufficient_evidence" in parsed:
                return parsed
            return None
        return parsed

    def _normalize_updates(
        self,
        raw: dict[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
        updates = raw.get("updates") if isinstance(raw.get("updates"), dict) else raw
        evidence = raw.get("evidence") if isinstance(raw.get("evidence"), list) else []
        insufficient = (
            raw.get("insufficient_evidence")
            if isinstance(raw.get("insufficient_evidence"), list)
            else []
        )

        normalized: dict[str, Any] = {}

        knowledge_base = updates.get("knowledge_base")
        if isinstance(knowledge_base, dict):
            clean: dict[str, Any] = {}
            level = self._normalize_level(knowledge_base.get("level"))
            if level:
                clean["level"] = level
            subjects = self._clean_string_list(knowledge_base.get("subjects"))
            if subjects:
                clean["subjects"] = subjects
            if clean:
                normalized["knowledge_base"] = clean

        cognitive_style = updates.get("cognitive_style")
        if isinstance(cognitive_style, dict):
            clean = {}
            preference = self._normalize_preference(cognitive_style.get("preference"))
            if preference:
                clean["preference"] = preference
            description = self._clean_string(cognitive_style.get("description"))
            if description:
                clean["description"] = description
            if clean:
                normalized["cognitive_style"] = clean

        learning_goals = updates.get("learning_goals")
        if isinstance(learning_goals, dict):
            clean = {}
            short_term = self._clean_string(learning_goals.get("short_term"))
            long_term = self._clean_string(learning_goals.get("long_term"))
            if short_term:
                clean["short_term"] = short_term
            if long_term:
                clean["long_term"] = long_term
            if clean:
                normalized["learning_goals"] = clean

        learning_pace = updates.get("learning_pace")
        if isinstance(learning_pace, dict):
            clean = {}
            speed = self._normalize_speed(learning_pace.get("speed"))
            if speed:
                clean["speed"] = speed
            minutes = learning_pace.get("preferred_session_minutes")
            if isinstance(minutes, int) and 5 <= minutes <= 240:
                clean["preferred_session_minutes"] = minutes
            if clean:
                normalized["learning_pace"] = clean

        interest_direction = updates.get("interest_direction")
        if isinstance(interest_direction, dict):
            areas = self._clean_string_list(interest_direction.get("areas"))
            if areas:
                normalized["interest_direction"] = {"areas": areas}

        for list_key in ("knowledge_gaps", "weak_points"):
            values = self._clean_string_list(updates.get(list_key))
            if values:
                normalized[list_key] = values

        clean_evidence: list[dict[str, Any]] = []
        for item in evidence:
            if not isinstance(item, dict):
                continue
            field = self._clean_string(item.get("field"))
            quote = self._clean_string(item.get("quote"))
            confidence = item.get("confidence")
            if not field or not quote:
                continue
            clean_item: dict[str, Any] = {"field": field, "quote": quote}
            if isinstance(confidence, (int, float)):
                clean_item["confidence"] = max(0, min(1, float(confidence)))
            clean_evidence.append(clean_item)

        clean_insufficient = [
            text for text in (self._clean_string(item) for item in insufficient) if text
        ]
        return normalized, clean_evidence, clean_insufficient

    def _extract_rule_updates(
        self,
        message: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        updates: dict[str, Any] = {}
        evidence: list[dict[str, Any]] = []
        text = message.strip()
        if not text:
            return updates, evidence

        level = self._normalize_level(text)
        if level:
            self._set_nested_update(updates, "knowledge_base", "level", level)
            evidence.append(self._evidence("knowledge_base.level", self._short_quote(text), 0.8))

        for field_type, pattern in RULE_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                value = self._clean_extracted_phrase(match.group(1))
                if not value:
                    continue

                if field_type == "knowledge_subjects":
                    subjects = self._split_items(value)
                    if subjects:
                        self._set_nested_update(updates, "knowledge_base", "subjects", subjects)
                        evidence.append(self._evidence("knowledge_base.subjects", match.group(0), 0.85))
                elif field_type == "knowledge_gaps":
                    gaps = self._split_items(value)
                    if gaps:
                        self._set_list_update(updates, "knowledge_gaps", gaps)
                        self._set_list_update(updates, "weak_points", gaps)
                        evidence.append(self._evidence("knowledge_gaps", match.group(0), 0.85))
                elif field_type == "short_goal":
                    self._set_nested_update(updates, "learning_goals", "short_term", value)
                    evidence.append(self._evidence("learning_goals.short_term", match.group(0), 0.9))
                elif field_type == "long_goal":
                    self._set_nested_update(updates, "learning_goals", "long_term", value)
                    evidence.append(self._evidence("learning_goals.long_term", match.group(0), 0.9))
                elif field_type == "interest":
                    areas = self._split_items(value)
                    if areas:
                        self._set_nested_update(updates, "interest_direction", "areas", areas)
                        evidence.append(self._evidence("interest_direction.areas", match.group(0), 0.85))
                elif field_type == "preference":
                    preference = self._normalize_preference(value)
                    if preference:
                        self._set_nested_update(updates, "cognitive_style", "preference", preference)
                    self._set_nested_update(updates, "cognitive_style", "description", value)
                    evidence.append(self._evidence("cognitive_style.description", match.group(0), 0.8))
                elif field_type == "pace":
                    speed = self._normalize_speed(value)
                    if speed:
                        self._set_nested_update(updates, "learning_pace", "speed", speed)
                        evidence.append(self._evidence("learning_pace.speed", match.group(0), 0.75))

        preference = self._normalize_preference(text)
        if preference and "cognitive_style" not in updates:
            self._set_nested_update(updates, "cognitive_style", "preference", preference)
            self._set_nested_update(updates, "cognitive_style", "description", self._short_quote(text))
            evidence.append(self._evidence("cognitive_style.preference", self._short_quote(text), 0.7))

        normalized, clean_evidence, _ = self._normalize_updates(
            {"updates": updates, "evidence": evidence}
        )
        return normalized, clean_evidence

    def _apply_updates(
        self,
        current: dict[str, Any],
        updates: dict[str, Any],
        evidence: list[dict[str, Any]],
        insufficient: list[str],
    ) -> tuple[dict[str, Any], list[str]]:
        next_profile = deepcopy(current)
        changed_fields: list[str] = []

        for key, value in updates.items():
            if isinstance(next_profile.get(key), dict) and isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, list):
                        merged = self._merge_lists(next_profile[key].get(sub_key), sub_value)
                        if merged != next_profile[key].get(sub_key):
                            next_profile[key][sub_key] = merged
                            changed_fields.append(f"{key}.{sub_key}")
                    elif next_profile[key].get(sub_key) != sub_value:
                        next_profile[key][sub_key] = sub_value
                        changed_fields.append(f"{key}.{sub_key}")
            elif isinstance(next_profile.get(key), list) and isinstance(value, list):
                merged = self._merge_lists(next_profile.get(key), value)
                if merged != next_profile.get(key):
                    next_profile[key] = merged
                    changed_fields.append(key)

        if changed_fields:
            meta = next_profile.setdefault("_meta", {})
            evidence_log = meta.setdefault("evidence", [])
            now = datetime.now(timezone.utc).isoformat()
            for item in evidence:
                evidence_log.append({**item, "updated_at": now})
            meta["last_analysis"] = {
                "updated_fields": changed_fields,
                "insufficient_evidence": insufficient,
                "analyzed_at": now,
            }
            meta["evidence"] = evidence_log[-50:]

        return next_profile, changed_fields

    def _merge_update_dicts(self, *items: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for item in items:
            for key, value in item.items():
                if isinstance(value, dict):
                    target = merged.setdefault(key, {})
                    if not isinstance(target, dict):
                        merged[key] = deepcopy(value)
                        continue
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, list):
                            target[sub_key] = self._merge_lists(target.get(sub_key), sub_value)
                        else:
                            target[sub_key] = sub_value
                elif isinstance(value, list):
                    merged[key] = self._merge_lists(merged.get(key), value)
                else:
                    merged[key] = value
        return merged

    def _normalize_level(self, value: Any) -> str:
        return self._normalize_enum(value, LEVEL_ALIASES, ALLOWED_LEVELS)

    def _normalize_preference(self, value: Any) -> str:
        return self._normalize_enum(value, PREFERENCE_ALIASES, ALLOWED_PREFERENCES)

    def _normalize_speed(self, value: Any) -> str:
        return self._normalize_enum(value, SPEED_ALIASES, ALLOWED_SPEEDS)

    def _normalize_enum(
        self,
        value: Any,
        aliases: dict[str, str],
        allowed: set[str],
    ) -> str:
        text = self._clean_string(value)
        if not text:
            return ""
        lowered = text.lower()
        if lowered in allowed:
            return lowered
        for alias, canonical in aliases.items():
            if alias.lower() in lowered:
                return canonical
        return ""

    def _split_items(self, value: str) -> list[str]:
        text = self._clean_extracted_phrase(value)
        if not text:
            return []
        parts = re.split(r"[、,，/；;]|以及|和|还有", text)
        cleaned: list[str] = []
        seen = set()
        for part in parts:
            item = self._clean_extracted_phrase(part)
            item = re.sub(r"^(熟悉|掌握|会)\s*", "", item)
            if self._normalize_level(item) and len(item) <= 4:
                continue
            if item and item not in seen:
                cleaned.append(item)
                seen.add(item)
        return cleaned

    def _clean_extracted_phrase(self, value: Any) -> str:
        text = self._clean_string(value)
        if not text:
            return ""
        text = re.sub(r"^(主要|比较|特别|更|偏|想要|想|希望|需要|包括)\s*", "", text)
        text = re.sub(r"\s*(这些|这类|方面|方向|内容)$", "", text)
        return text.strip(" ：:，,。；;")

    @staticmethod
    def _set_nested_update(
        updates: dict[str, Any],
        key: str,
        sub_key: str,
        value: Any,
    ) -> None:
        if not value:
            return
        section = updates.setdefault(key, {})
        if isinstance(value, list):
            existing = section.get(sub_key)
            merged = []
            seen = set()
            for item in [*(existing if isinstance(existing, list) else []), *value]:
                text = str(item).strip()
                if text and text not in seen:
                    merged.append(text)
                    seen.add(text)
            section[sub_key] = merged
        else:
            section[sub_key] = value

    @staticmethod
    def _set_list_update(updates: dict[str, Any], key: str, values: list[str]) -> None:
        existing = updates.get(key)
        merged = []
        seen = set()
        for item in [*(existing if isinstance(existing, list) else []), *values]:
            text = str(item).strip()
            if text and text not in seen:
                merged.append(text)
                seen.add(text)
        if merged:
            updates[key] = merged

    @staticmethod
    def _evidence(field: str, quote: str, confidence: float) -> dict[str, Any]:
        return {
            "field": field,
            "quote": quote[:120],
            "confidence": confidence,
        }

    @staticmethod
    def _short_quote(text: str) -> str:
        return text.strip().replace("\n", " ")[:120]

    @staticmethod
    def _clean_string(value: Any) -> str:
        if not isinstance(value, str):
            return ""
        value = value.strip()
        if value.lower() in {"", "unknown", "unset", "none", "null", "n/a", "na"}:
            return ""
        if value in {
            "暂无",
            "未设置",
            "未知",
            "无",
            "没有",
            "不确定",
        }:
            return ""
        return value

    @classmethod
    def _clean_string_list(cls, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        cleaned = []
        seen = set()
        for item in value:
            text = cls._clean_string(item)
            if text and text not in seen:
                cleaned.append(text)
                seen.add(text)
        return cleaned

    @staticmethod
    def _merge_lists(existing: Any, incoming: list[str]) -> list[str]:
        merged = []
        seen = set()
        source = existing if isinstance(existing, list) else []
        for item in [*source, *incoming]:
            text = str(item).strip()
            if text and text not in seen:
                merged.append(text)
                seen.add(text)
        return merged
