"""Deterministic post-generation quality review for resource agents.

Pure component: no I/O, no async, no side effects. Takes generated content and
resource type, returns a typed ReviewResult with status, score, and issues.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ReviewResult:
    """Result of a post-generation quality review."""

    status: str  # "passed" or "needs_review"
    score: float  # 0.0 - 1.0
    issues: list[str] = field(default_factory=list)


class ResourceReviewer:
    """Deterministic quality reviewer for generated learning resources.

    Validates non-empty content and type-specific minimum evidence for each
    of the six resource types.  Pure function: no state, no side effects.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def review(self, resource_type: str, content: str | None) -> ReviewResult:
        """Review generated content and return a typed result.

        Args:
            resource_type: One of document, mindmap, exercise, code, reading, video.
            content: The generated content string (may be None or empty).

        Returns:
            ReviewResult with status, score, and issues list.
        """
        issues: list[str] = []

        # 1. Non-empty content check (applies to all types)
        if not content or not content.strip():
            return ReviewResult(status="needs_review", score=0.0, issues=["content is empty"])

        # 2. Type-specific evidence checks
        type_issues = self._check_type_evidence(resource_type, content)
        issues.extend(type_issues)

        # 3. Compute score and status
        score = self._compute_score(resource_type, issues)
        status = "passed" if score >= 0.8 else "needs_review"

        return ReviewResult(status=status, score=score, issues=issues)

    # ------------------------------------------------------------------
    # Score computation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_score(resource_type: str, issues: list[str]) -> float:
        """Compute a numeric score from issues.

        Each resource type has a baseline of 1.0.  Each issue deducts a
        type-specific penalty.  Score is clamped to [0.0, 1.0].
        """
        if not issues:
            return 1.0

        penalties: dict[str, float] = {
            "document": 0.4,
            "mindmap": 0.35,
            "exercise": 0.35,
            "code": 0.35,
            "reading": 0.4,
            "video": 0.25,
        }
        penalty = penalties.get(resource_type, 0.4)
        score = 1.0 - (len(issues) * penalty)
        return max(0.0, min(1.0, round(score, 2)))

    # ------------------------------------------------------------------
    # Type-specific evidence checks
    # ------------------------------------------------------------------

    def _check_type_evidence(self, resource_type: str, content: str) -> list[str]:
        """Dispatch to the appropriate type-specific validator."""
        handlers: dict[str, object] = {
            "document": self._check_document,
            "mindmap": self._check_mindmap,
            "exercise": self._check_exercise,
            "code": self._check_code,
            "reading": self._check_reading,
            "video": self._check_video,
        }
        handler = handlers.get(resource_type)
        if handler is None:
            return [f"unknown resource type: {resource_type}"]
        return handler(content)  # type: ignore[operator]

    # ------------------------------------------------------------------
    # Document / Reading: substantive text
    # ------------------------------------------------------------------

    def _check_document(self, content: str) -> list[str]:
        return self._check_substantive_text(content, "document")

    def _check_reading(self, content: str) -> list[str]:
        return self._check_substantive_text(content, "reading")

    @staticmethod
    def _check_substantive_text(content: str, label: str) -> list[str]:
        """Document and reading must contain substantive text."""
        issues: list[str] = []
        stripped = content.strip()

        # Minimum character count (excludes trivial error messages)
        if len(stripped) < 80:
            issues.append(f"{label} content too short ({len(stripped)} chars, need >= 80)")

        # Must contain at least one paragraph-like structure
        paragraphs = [p for p in stripped.split("\n") if len(p.strip()) >= 20]
        if len(paragraphs) < 2:
            issues.append(f"{label} lacks substantive paragraphs (found {len(paragraphs)} with >= 20 chars)")

        return issues

    # ------------------------------------------------------------------
    # Mindmap: Mermaid-like syntax
    # ------------------------------------------------------------------

    @staticmethod
    def _check_mindmap(content: str) -> list[str]:
        """Mindmap must contain Mermaid-like syntax markers."""
        issues: list[str] = []
        lower = content.lower()

        mermaid_markers = [
            "```mermaid",
            "graph ",
            "flowchart ",
            "mindmap",
            "gantt",
            "sequenceDiagram",
            "classDiagram",
            "stateDiagram",
            "erDiagram",
            "pie",
            "-->",
            "---",
        ]
        found = any(marker in lower for marker in mermaid_markers)
        if not found:
            issues.append("mindmap content does not contain Mermaid-like syntax")

        return issues

    # ------------------------------------------------------------------
    # Exercise: answer / 解析 markers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_exercise(content: str) -> list[str]:
        """Exercise must contain answer or 解析 markers."""
        issues: list[str] = []

        answer_markers = [
            "答案",
            "解析",
            "解答",
            "参考答案",
            "answer",
            "solution",
            "explanation",
        ]
        found = any(marker in content for marker in answer_markers)
        if not found:
            issues.append("exercise content does not contain answer/解析 markers")

        return issues

    # ------------------------------------------------------------------
    # Code: code fence or common code markers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_code(content: str) -> list[str]:
        """Code resource must contain a code fence or common code markers."""
        issues: list[str] = []

        # Code fence (```)
        if "```" in content:
            return issues

        # Common code markers across languages
        code_markers = [
            r"\bdef\s+\w+\s*\(",       # Python function
            r"\bclass\s+\w+",          # class definition
            r"\bimport\s+\w+",         # import statement
            r"\bfrom\s+\w+\s+import",  # from X import
            r"\bfunction\s+\w+\s*\(",  # JS/TS function
            r"\bconst\s+\w+\s*=",      # JS const
            r"\blet\s+\w+\s*=",        # JS let
            r"\bvar\s+\w+\s*=",        # JS var
            r"\bpublic\s+(static\s+)?(void|int|String|class)",  # Java
            r"\bpackage\s+\w+",        # Go/Java package
            r"\bfn\s+\w+\s*\(",        # Rust fn
            r"#include\s*<",           # C/C++ include
            r"\bprint\(",              # print statement
            r"\bconsole\.log\(",       # console.log
            r"\bSystem\.out\.print",   # Java print
            r"\bif\s+__name__\s*==\s*[\"']__main__[\"']",  # Python main
        ]
        found = any(re.search(pattern, content) for pattern in code_markers)
        if not found:
            issues.append("code content does not contain a code fence or recognizable code markers")

        return issues

    # ------------------------------------------------------------------
    # Video: valid JSON, mode=video_like_slides, non-empty slides, quality
    # ------------------------------------------------------------------

    # Template phrases that indicate low-quality generated content
    _TEMPLATE_PHRASES = (
        "这一页围绕",
        "本镜头建立学习目标",
        "本页围绕",
        "本节将围绕",
        "通过本页学习",
    )

    @classmethod
    def _check_video(cls, content: str) -> list[str]:
        """Video must be valid JSON with mode=video_like_slides and non-empty slides."""
        issues: list[str] = []

        # Parse JSON
        try:
            data = json.loads(content)
        except (TypeError, json.JSONDecodeError):
            issues.append("video content is not valid JSON")
            return issues

        if not isinstance(data, dict):
            issues.append("video content JSON is not an object")
            return issues

        # Check mode
        if data.get("mode") != "video_like_slides":
            issues.append('video mode is not "video_like_slides"')

        # Check slides
        slides = data.get("slides")
        if not isinstance(slides, list):
            issues.append("video slides is not a list")
            return issues

        if not slides:
            issues.append("video slides list is empty")
            return issues

        # Inline quality validation (avoids heavy VideoAgent import chain)
        cls._validate_video_slides(slides, issues)

        return issues

    @classmethod
    def _validate_video_slides(cls, slides: list[dict], issues: list[str]) -> None:
        """Validate slide quality: case_detail length, bullet-title similarity, template phrases, cross-slide similarity."""
        slide_texts: list[tuple[int, str]] = []

        for index, slide in enumerate(slides, 1):
            if not isinstance(slide, dict):
                issues.append(f"slide {index} is not a dict")
                continue

            title = str(slide.get("title") or "")
            bullets = [str(item) for item in slide.get("bullets", [])]
            case_detail = str(slide.get("case_detail") or "").strip()
            examples = [str(item) for item in slide.get("examples", [])]
            slide_text = "\n".join(
                [
                    title,
                    "\n".join(bullets),
                    "\n".join(str(item) for item in slide.get("key_points", [])),
                    case_detail,
                    "\n".join(examples),
                    str(slide.get("caption") or ""),
                    str(slide.get("teacher_script") or ""),
                ]
            )
            slide_texts.append((index, slide_text))

            if len(case_detail) < 60 and "教材中未提供具体案例" not in case_detail:
                issues.append(f"slide {index} case_detail too short ({len(case_detail)} chars)")

            repeated_bullets = [
                bullet
                for bullet in bullets
                if title and (title in bullet or cls._text_similarity(title, bullet) >= 0.72)
            ]
            if len(repeated_bullets) >= max(2, len(bullets) // 2):
                issues.append(f"slide {index} bullets highly repeat title")

            if any(phrase in slide_text for phrase in cls._TEMPLATE_PHRASES):
                issues.append(f"slide {index} contains template phrase")

        for left_pos, (left_index, left_text) in enumerate(slide_texts):
            for right_index, right_text in slide_texts[left_pos + 1 :]:
                if cls._text_similarity(left_text, right_text) >= 0.82:
                    issues.append(f"slides {left_index} and {right_index} are too similar")

    @staticmethod
    def _text_signature(text: str) -> set[str]:
        clean = "".join(ch.lower() for ch in str(text or "") if not ch.isspace())
        if len(clean) < 2:
            return {clean} if clean else set()
        return {clean[i : i + 2] for i in range(len(clean) - 1)}

    @classmethod
    def _text_similarity(cls, left: str, right: str) -> float:
        left_sig = cls._text_signature(left)
        right_sig = cls._text_signature(right)
        if not left_sig or not right_sig:
            return 0.0
        return len(left_sig & right_sig) / len(left_sig | right_sig)
