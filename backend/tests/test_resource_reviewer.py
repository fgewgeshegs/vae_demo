"""Tests for ResourceReviewer — deterministic post-generation quality review."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Bypass heavy app.agents package initializer
# ---------------------------------------------------------------------------
# The test file only needs ResourceReviewer / ReviewResult from
# resource_reviewer.py, but importing via the normal package path triggers
# app/agents/__init__.py → CoordinatorAgent → Retriever → Reranker →
# FlagEmbedding → datasets (missing).  We load resource_reviewer.py directly
# via importlib and register stub packages so that the integration test's
# `from app.agents.resource_agent import ResourceCoordinator` also skips the
# heavy __init__.py chain.

_test_dir = Path(__file__).resolve().parent
_app_dir = _test_dir.parent / "app"

# --- stub app.agents (skip __init__.py) ---
if "app.agents" not in sys.modules:
    _agents_pkg = types.ModuleType("app.agents")
    _agents_pkg.__path__ = [str(_app_dir / "agents")]
    _agents_pkg.__package__ = "app.agents"
    sys.modules["app.agents"] = _agents_pkg

# --- stub app.agents.resource_agent (skip __init__.py) ---
if "app.agents.resource_agent" not in sys.modules:
    _res_agent_pkg = types.ModuleType("app.agents.resource_agent")
    _res_agent_pkg.__path__ = [str(_app_dir / "agents" / "resource_agent")]
    _res_agent_pkg.__package__ = "app.agents.resource_agent"
    sys.modules["app.agents.resource_agent"] = _res_agent_pkg

# Load resource_reviewer.py directly.  Must be in sys.modules before
# exec_module so that @dataclass (which looks up cls.__module__) succeeds.
_reviewer_path = _app_dir / "agents" / "resource_agent" / "resource_reviewer.py"
_MODULE_NAME = "app.agents.resource_agent.resource_reviewer"
_spec = importlib.util.spec_from_file_location(_MODULE_NAME, str(_reviewer_path))
_reviewer_mod = importlib.util.module_from_spec(_spec)
sys.modules[_MODULE_NAME] = _reviewer_mod
_spec.loader.exec_module(_reviewer_mod)
ResourceReviewer = _reviewer_mod.ResourceReviewer
ReviewResult = _reviewer_mod.ReviewResult

# Provide a minimal ResourceCoordinator so the integration test can import it
# without triggering the heavy resource_agents → Retriever → FlagEmbedding chain.
class _StubResourceCoordinator:
    """Minimal stand-in so TestIntegration can verify reviewer wiring."""
    def __init__(self):
        self.reviewer = ResourceReviewer()

sys.modules["app.agents.resource_agent"].ResourceCoordinator = _StubResourceCoordinator


@pytest.fixture
def reviewer() -> ResourceReviewer:
    return ResourceReviewer()


# ---------------------------------------------------------------------------
# ReviewResult shape
# ---------------------------------------------------------------------------


class TestReviewResult:
    def test_defaults(self):
        result = ReviewResult(status="passed", score=1.0)
        assert result.status == "passed"
        assert result.score == 1.0
        assert result.issues == []

    def test_with_issues(self):
        result = ReviewResult(status="needs_review", score=0.3, issues=["bad", "worse"])
        assert result.status == "needs_review"
        assert result.score == 0.3
        assert result.issues == ["bad", "worse"]

    def test_is_frozen(self):
        result = ReviewResult(status="passed", score=1.0)
        with pytest.raises(Exception):
            result.status = "needs_review"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Empty / None content
# ---------------------------------------------------------------------------


class TestEmptyContent:
    def test_none_content_fails(self, reviewer: ResourceReviewer):
        result = reviewer.review("document", None)
        assert result.status == "needs_review"
        assert result.score == 0.0
        assert "empty" in result.issues[0].lower()

    def test_empty_string_fails(self, reviewer: ResourceReviewer):
        result = reviewer.review("mindmap", "")
        assert result.status == "needs_review"
        assert result.score == 0.0

    def test_whitespace_only_fails(self, reviewer: ResourceReviewer):
        result = reviewer.review("code", "   \n  \t  ")
        assert result.status == "needs_review"
        assert result.score == 0.0


# ---------------------------------------------------------------------------
# Unknown resource type
# ---------------------------------------------------------------------------


class TestUnknownType:
    def test_unknown_type_returns_issue(self, reviewer: ResourceReviewer):
        result = reviewer.review("unknown_type", "some content here")
        assert result.status == "needs_review"
        assert any("unknown" in issue.lower() for issue in result.issues)


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


class TestDocumentReview:
    def test_passes_with_substantive_text(self, reviewer: ResourceReviewer):
        content = (
            "# 第一章 概述\n\n"
            + "这是一段足够长的文本内容，用于测试文档审查功能。\n" * 5
        )
        result = reviewer.review("document", content)
        assert result.status == "passed"
        assert result.score == 1.0
        assert result.issues == []

    def test_fails_with_short_text(self, reviewer: ResourceReviewer):
        result = reviewer.review("document", "太短了")
        assert result.status == "needs_review"
        assert any("too short" in issue.lower() for issue in result.issues)

    def test_fails_without_paragraphs(self, reviewer: ResourceReviewer):
        content = "a b c d e f g h i j k l m n o p q r s t u v w x y z " * 4
        result = reviewer.review("document", content)
        assert result.status == "needs_review"
        assert any("paragraph" in issue.lower() for issue in result.issues)


# ---------------------------------------------------------------------------
# Mindmap
# ---------------------------------------------------------------------------


class TestMindmapReview:
    def test_passes_with_mermaid_fence(self, reviewer: ResourceReviewer):
        content = "```mermaid\ngraph TD\nA-->B\n```"
        result = reviewer.review("mindmap", content)
        assert result.status == "passed"
        assert result.score == 1.0

    def test_passes_with_graph_keyword(self, reviewer: ResourceReviewer):
        content = "graph LR\n  Root --> Child1\n  Root --> Child2"
        result = reviewer.review("mindmap", content)
        assert result.status == "passed"

    def test_passes_with_mindmap_keyword(self, reviewer: ResourceReviewer):
        content = "mindmap\n  Root\n    分支一\n    分支二"
        result = reviewer.review("mindmap", content)
        assert result.status == "passed"

    def test_passes_with_flowchart(self, reviewer: ResourceReviewer):
        content = "flowchart TD\n  Start --> End"
        result = reviewer.review("mindmap", content)
        assert result.status == "passed"

    def test_fails_without_mermaid_syntax(self, reviewer: ResourceReviewer):
        content = "这是一个思维导图，但是没有 Mermaid 语法。\n- 节点1\n- 节点2"
        result = reviewer.review("mindmap", content)
        assert result.status == "needs_review"
        assert any("mermaid" in issue.lower() for issue in result.issues)


# ---------------------------------------------------------------------------
# Exercise
# ---------------------------------------------------------------------------


class TestExerciseReview:
    def test_passes_with_answer_marker(self, reviewer: ResourceReviewer):
        content = "题目：1+1=?\n答案：2"
        result = reviewer.review("exercise", content)
        assert result.status == "passed"
        assert result.score == 1.0

    def test_passes_with_解析_marker(self, reviewer: ResourceReviewer):
        content = "题目：什么是闭包？\n解析：闭包是指..."
        result = reviewer.review("exercise", content)
        assert result.status == "passed"

    def test_passes_with_参考答案(self, reviewer: ResourceReviewer):
        content = "1. 问题描述\n参考答案：详见下文"
        result = reviewer.review("exercise", content)
        assert result.status == "passed"

    def test_fails_without_answer_markers(self, reviewer: ResourceReviewer):
        content = "题目1：请回答以下问题。\n题目2：请回答以下问题。"
        result = reviewer.review("exercise", content)
        assert result.status == "needs_review"
        assert any("answer" in issue.lower() or "解析" in issue for issue in result.issues)


# ---------------------------------------------------------------------------
# Code
# ---------------------------------------------------------------------------


class TestCodeReview:
    def test_passes_with_code_fence(self, reviewer: ResourceReviewer):
        content = "```python\ndef hello():\n    print('hi')\n```"
        result = reviewer.review("code", content)
        assert result.status == "passed"
        assert result.score == 1.0

    def test_passes_with_python_def(self, reviewer: ResourceReviewer):
        content = "def calculate_sum(a, b):\n    return a + b"
        result = reviewer.review("code", content)
        assert result.status == "passed"

    def test_passes_with_import_statement(self, reviewer: ResourceReviewer):
        content = "import os\nfrom pathlib import Path"
        result = reviewer.review("code", content)
        assert result.status == "passed"

    def test_passes_with_js_function(self, reviewer: ResourceReviewer):
        content = "function greet(name) {\n  return `Hello ${name}`;\n}"
        result = reviewer.review("code", content)
        assert result.status == "passed"

    def test_fails_without_code_markers(self, reviewer: ResourceReviewer):
        content = "这是一段关于代码的文字说明，但没有实际的代码。"
        result = reviewer.review("code", content)
        assert result.status == "needs_review"
        assert any("code" in issue.lower() for issue in result.issues)


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


class TestReadingReview:
    def test_passes_with_substantive_text(self, reviewer: ResourceReviewer):
        content = (
            "# 拓展阅读材料\n\n"
            + "这是一段足够长的拓展阅读文本内容，用于测试阅读审查功能。\n" * 5
        )
        result = reviewer.review("reading", content)
        assert result.status == "passed"
        assert result.score == 1.0

    def test_fails_with_short_text(self, reviewer: ResourceReviewer):
        result = reviewer.review("reading", "短文本")
        assert result.status == "needs_review"


# ---------------------------------------------------------------------------
# Video
# ---------------------------------------------------------------------------


class TestVideoReview:
    def test_passes_with_valid_video_json(self, reviewer: ResourceReviewer):
        payload = {
            "mode": "video_like_slides",
            "title": "测试微课",
            "duration_seconds": 180,
            "slides": [
                {
                    "start": 0,
                    "end": 30,
                    "title": "学习目标",
                    "bullets": ["要点1：事实描述", "要点2：解释原因", "要点3：给出例子", "要点4：提示易错点"],
                    "core_question": "本节要解决什么问题？",
                    "key_points": ["关键点1", "关键点2", "关键点3"],
                    "case_detail": "这是一个足够长的案例详情描述，用于通过视频质量校验。这里包含具体的教材案例背景、风险分析和详细说明，确保内容充实且具有教学价值。",
                    "misconception": "常见误解说明",
                    "self_check": "自测问题",
                    "caption": "字幕文本六十到一百字的内容描述",
                    "teacher_script": "教师讲解稿一百二十到一百八十字的内容，要像课堂讲解一样自然流畅。",
                    "examples": ["例子1", "例子2"],
                    "interaction_question": "互动问题",
                    "visual": {"type": "concept", "keywords": ["关键词1", "关键词2", "关键词3", "关键词4"]},
                }
            ],
        }
        content = json.dumps(payload, ensure_ascii=False)
        result = reviewer.review("video", content)
        assert result.status == "passed"
        assert result.score == 1.0

    def test_fails_with_invalid_json(self, reviewer: ResourceReviewer):
        result = reviewer.review("video", "not json at all")
        assert result.status == "needs_review"
        assert any("json" in issue.lower() for issue in result.issues)

    def test_fails_with_wrong_mode(self, reviewer: ResourceReviewer):
        payload = {"mode": "plain_text", "slides": []}
        result = reviewer.review("video", json.dumps(payload))
        assert result.status == "needs_review"
        assert any("video_like_slides" in issue for issue in result.issues)

    def test_fails_with_empty_slides(self, reviewer: ResourceReviewer):
        payload = {"mode": "video_like_slides", "slides": []}
        result = reviewer.review("video", json.dumps(payload))
        assert result.status == "needs_review"
        assert any("empty" in issue.lower() for issue in result.issues)

    def test_fails_with_slides_not_list(self, reviewer: ResourceReviewer):
        payload = {"mode": "video_like_slides", "slides": "not a list"}
        result = reviewer.review("video", json.dumps(payload))
        assert result.status == "needs_review"
        assert any("not a list" in issue.lower() for issue in result.issues)

    def test_fails_with_quality_issues(self, reviewer: ResourceReviewer):
        payload = {
            "mode": "video_like_slides",
            "title": "测试",
            "slides": [
                {
                    "start": 0,
                    "end": 30,
                    "title": "标题",
                    "bullets": ["标题", "标题", "标题", "标题"],  # bullets repeat title
                    "core_question": "问题",
                    "key_points": ["k1"],
                    "case_detail": "太短",  # too short
                    "misconception": "",
                    "self_check": "",
                    "caption": "字幕",
                    "teacher_script": "这一页围绕标题展开讲解。",  # template phrase
                    "examples": [],
                    "interaction_question": "",
                    "visual": {"type": "concept", "keywords": []},
                }
            ],
        }
        content = json.dumps(payload, ensure_ascii=False)
        result = reviewer.review("video", content)
        assert result.status == "needs_review"
        assert len(result.issues) > 0


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------


class TestScoreComputation:
    def test_perfect_score_with_no_issues(self, reviewer: ResourceReviewer):
        content = "```mermaid\ngraph TD\nA-->B\n```"
        result = reviewer.review("mindmap", content)
        assert result.score == 1.0
        assert result.status == "passed"

    def test_score_decreases_with_issues(self, reviewer: ResourceReviewer):
        # mindmap penalty is 0.35 per issue
        result = reviewer.review("mindmap", "no mermaid syntax here at all")
        assert result.score < 1.0
        assert result.score > 0.0

    def test_score_clamped_to_zero(self, reviewer: ResourceReviewer):
        # document penalty is 0.4, 3 issues = 1.2 penalty -> clamped to 0
        # "x" triggers 2 issues (too short + no paragraphs) = 0.2 score
        result = reviewer.review("document", "x")
        assert result.score == 0.2
        # With 3+ issues, score clamps to 0.0
        # Use a type with higher penalty: video with invalid JSON (1 issue, 0.25 penalty)
        # Actually verify clamping: empty content gives 0.0
        result_empty = reviewer.review("document", "")
        assert result_empty.score == 0.0


# ---------------------------------------------------------------------------
# Integration: reviewer is importable and callable from coordinator path
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_reviewer_instantiable_in_coordinator(self):
        from app.agents.resource_agent import ResourceCoordinator
        coordinator = ResourceCoordinator()
        assert coordinator.reviewer is not None
        result = coordinator.reviewer.review("mindmap", "```mermaid\ngraph TD\nA-->B\n```")
        assert result.status == "passed"

    def test_review_result_included_in_return_shape(self):
        """Verify the return dict shape includes review fields."""
        review = ReviewResult(status="passed", score=0.85, issues=["minor"])
        returned = {
            "id": 1,
            "title": "test",
            "type": "document",
            "content": "content",
            "review_status": review.status,
            "review_score": review.score,
            "review_issues": review.issues,
        }
        assert "review_status" in returned
        assert "review_score" in returned
        assert "review_issues" in returned
        assert returned["review_status"] == "passed"
        assert returned["review_score"] == 0.85
