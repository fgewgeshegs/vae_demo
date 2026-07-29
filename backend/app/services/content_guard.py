"""Minimal, testable content-safety and hallucination guard for the RAG boundary.

Integrates at agent output level (QAAgent / CoordinatorAgent) rather than
mutating every LLM completion. Provides:

- Prompt rejection for a conservative set of explicit harmful/sensitive patterns
- No-context marking when retrieval returns zero results
- Unsupported-citation detection in generated answers
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class GuardDecision(str, Enum):
    PASS = "pass"
    REJECT = "reject"
    FLAG_NO_CONTEXT = "flag_no_context"
    FLAG_UNSUPPORTED_CITATION = "flag_unsupported_citation"


@dataclass(frozen=True, slots=True)
class GuardResult:
    decision: GuardDecision
    safe_message: str = ""
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Conservative prompt-rejection patterns — explicit, unambiguous harmful content
# ---------------------------------------------------------------------------

_REJECT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Self-harm / suicide methods
    (
        re.compile(
            r"(自杀|自残|割腕|上吊|跳楼|服毒|安眠药.*自杀|怎么.*死|如何.*结束.*生命|"
            r"suicide.*method|how.*(kill|end).*(myself|my life)|self.?harm.*instruction)",
            re.IGNORECASE,
        ),
        "你的消息包含不安全内容，请寻求专业帮助。如果你正在经历困难，可以联系心理援助热线。",
    ),
    # Child exploitation
    (
        re.compile(
            r"(儿童.*色情|未成年.*性|幼女|child.*porn|CSAM|underage.*sexual|"
            r"grooming.*child|lolita.*sex)",
            re.IGNORECASE,
        ),
        "你的消息包含不安全内容，已被拒绝。",
    ),
    # Explicit violence / threats against persons
    (
        re.compile(
            r"(我要杀了?你|弄死你|炸了.*学校|恐怖袭击.*教程|"
            r"how.*(build.*bomb|make.*explosive|commit.*mass.*shooting)|"
            r"terrorist.*manual)",
            re.IGNORECASE,
        ),
        "你的消息包含不安全内容，已被拒绝。",
    ),
    # Hate speech — explicit slurs + calls for violence
    (
        re.compile(
            r"(种族.*灭绝|消灭.*民族|屠杀.*(中国人|日本人|黑人|白人)|"
            r"genocide|ethnic.*cleansing|exterminate.*(race|ethnic))",
            re.IGNORECASE,
        ),
        "你的消息包含不安全内容，已被拒绝。",
    ),
    # Illegal activity instructions
    (
        re.compile(
            r"(制毒.*教程|毒品.*制作|黑客.*入侵.*教程|how.*(hack.*bank|launder.*money|"
            r"traffic.*drugs|smuggle.*weapons))",
            re.IGNORECASE,
        ),
        "你的消息包含不安全内容，已被拒绝。",
    ),
]

# ---------------------------------------------------------------------------
# Citation-integrity patterns — detect fabricated citations in answers
# ---------------------------------------------------------------------------

# Matches fabricated page/chapter citations like "（教材第12页）", "(教材第3章)",
# "[资料1]", "（第45页）", "参见教材P.23"
_UNSUPPORTED_CITATION_RE = re.compile(
    r"(教材第\s*\d+\s*[页章节]|（第\s*\d+\s*[页章节]）|\[资料\s*\d+\]|"
    r"参见教材\s*P\.?\s*\d+|\(教材.*第.*[页章节]\)|"
    r"\[来源\s*\d+\]|参考资料\s*\d+)"
)

# Matches fabricated source attributions like "根据教材第3章", "资料1显示"
_SOURCE_ATTRIBUTION_RE = re.compile(
    r"(根据教材|资料\d+\s*显示|教材中.*提到|课程资料.*指出|"
    r"第\s*\d+\s*[页章节].*指出)"
)

# ---------------------------------------------------------------------------
# No-context prefix — prepended when retrieval returned zero results
# ---------------------------------------------------------------------------

_NO_CONTEXT_PREFIX = (
    "⚠️ 课程知识库中未找到与该问题直接相关的内容。"
    "以下回答基于通用知识，可能不准确，建议参考课程教材或咨询教师。\n\n"
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ContentGuard:
    """Stateless guard with typed decisions. All methods are pure functions."""

    @staticmethod
    def check_prompt(prompt: str) -> GuardResult:
        """Check a user prompt for explicit harmful/sensitive content.

        Returns REJECT with a user-safe message if any reject pattern matches,
        otherwise PASS.
        """
        if not prompt or not prompt.strip():
            return GuardResult(decision=GuardDecision.PASS)

        for pattern, safe_message in _REJECT_PATTERNS:
            if pattern.search(prompt):
                return GuardResult(
                    decision=GuardDecision.REJECT,
                    safe_message=safe_message,
                )

        return GuardResult(decision=GuardDecision.PASS)

    @staticmethod
    def check_answer(
        answer: str,
        has_context: bool,
        source_count: int,
    ) -> GuardResult:
        """Check a generated answer for hallucination and integrity issues.

        - If no context was available, flags the answer and prepends a warning.
        - If no context was available but the answer contains fabricated
          citations, flags unsupported citations.
        - Otherwise PASS.
        """
        if not answer:
            return GuardResult(decision=GuardDecision.PASS)

        if has_context and source_count > 0:
            return GuardResult(decision=GuardDecision.PASS)

        # No retrieval context — the answer may be hallucinated
        warnings: list[str] = []
        decision = GuardDecision.FLAG_NO_CONTEXT

        # Check for fabricated citations when no context was available
        if _UNSUPPORTED_CITATION_RE.search(answer) or _SOURCE_ATTRIBUTION_RE.search(answer):
            decision = GuardDecision.FLAG_UNSUPPORTED_CITATION
            warnings.append(
                "生成的回答中包含未经验证的引用标注，"
                "当前检索未返回相关课程资料，这些引用可能不准确。"
            )

        return GuardResult(
            decision=decision,
            safe_message=_NO_CONTEXT_PREFIX + answer,
            warnings=warnings,
        )

    @staticmethod
    def wrap_no_context_answer(answer: str) -> str:
        """Prepend the no-context warning prefix to an answer."""
        return _NO_CONTEXT_PREFIX + answer
