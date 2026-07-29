from __future__ import annotations

import pytest
from fastapi import HTTPException
import asyncio
import importlib.util
from pathlib import Path

from app.core.config import apply_runtime_config, settings
from app.core.security import create_access_token, get_current_user, require_admin
from app.models.user import User
from app.services.bge_runtime import inference_slot
from app.services.retrieval_errors import RetrievalBusyError
from app.services.retrieval_policy import filter_relevant
from app.services.document_queue import _parse_payload
from app.services.sse import sse_event
from inference_service.batcher import DynamicBatcher


@pytest.mark.asyncio
async def test_invalid_jwt_subject_returns_401():
    token = create_access_token({"sub": "not-an-integer"})
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token=token, db=None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_non_admin_is_rejected():
    with pytest.raises(HTTPException) as exc:
        await require_admin(User(is_admin=False))
    assert exc.value.status_code == 403


def test_authentication_query_does_not_eager_load_history():
    assert User.profile.property.lazy == "raise"
    assert User.qa_records.property.lazy == "raise"
    assert User.learning_behaviors.property.lazy == "raise"


def test_runtime_config_applies_typed_value():
    original = settings.MAX_CHUNK_SIZE
    try:
        assert apply_runtime_config("max_chunk_size", "640")
        assert settings.MAX_CHUNK_SIZE == 640
    finally:
        settings.MAX_CHUNK_SIZE = original


def test_retrieval_threshold_is_centralized():
    results = filter_relevant(
        [{"score": 0.9}, {"score": 0.4}, {"score": 0.1}]
    )
    assert results == [{"score": 0.9}, {"score": 0.4}]


@pytest.mark.asyncio
async def test_gpu_queue_returns_busy_error():
    original_timeout = settings.BGE_QUEUE_TIMEOUT_SECONDS
    settings.BGE_QUEUE_TIMEOUT_SECONDS = 0.01
    try:
        async with inference_slot():
            with pytest.raises(RetrievalBusyError):
                async with inference_slot():
                    pass
    finally:
        settings.BGE_QUEUE_TIMEOUT_SECONDS = original_timeout


def test_coordinator_has_single_planning_round():
    source = (Path(__file__).parents[1] / "app" / "agents" / "coordinator.py").read_text(
        encoding="utf-8"
    )
    assert "range(1)" in source
    assert "range(3)" not in source


def test_learning_tasks_use_workflow_coordinator():
    source = (Path(__file__).parents[1] / "app" / "services" / "learning_task_service.py").read_text(
        encoding="utf-8"
    )
    assert "workflow_coordinator.run(task)" in source
    assert "_run_agent" not in source


def test_chat_api_uses_chat_coordinator():
    source = (Path(__file__).parents[1] / "app" / "api" / "v1" / "chat.py").read_text(
        encoding="utf-8"
    )
    assert "chat_coordinator.process" in source
    assert "from app.agents.coordinator import coordinator" not in source


def test_agent_protocol_normalizes_legacy_result():
    protocol_path = Path(__file__).parents[1] / "app" / "agents" / "agent_protocol.py"
    spec = importlib.util.spec_from_file_location("agent_protocol_for_test", protocol_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    result = module.normalize_agent_result(
        agent="PathAgent",
        raw={"type": "path", "message": "ok", "path_id": 1},
        type="study_path",
        success=True,
        artifacts=[{"type": "study_path", "id": 1}],
    )
    assert result == {
        "agent": "PathAgent",
        "status": "success",
        "type": "study_path",
        "data": {"type": "path", "message": "ok", "path_id": 1},
        "state_updates": [],
        "artifacts": [{"type": "study_path", "id": 1}],
        "next_actions": [],
        "errors": [],
        "message": "ok",
    }


def test_workflow_coordinator_records_agent_protocol_results():
    source = (Path(__file__).parents[1] / "app" / "agents" / "workflow_coordinator.py").read_text(
        encoding="utf-8"
    )
    assert "normalize_agent_result" in source
    assert '"agents": agent_results' in source
    assert '"agent": "PathAgent"' not in source


def test_document_queue_accepts_legacy_and_structured_jobs():
    assert _parse_payload("42") == {"doc_id": 42, "attempts": 0}
    assert _parse_payload('{"doc_id": 42, "attempts": 2}') == {
        "doc_id": 42,
        "attempts": 2,
    }


def test_sse_event_format():
    event = sse_event({"type": "delta", "content": "hello"}, "delta")
    assert event.startswith("event: delta\ndata: ")
    assert event.endswith("\n\n")


@pytest.mark.asyncio
async def test_dynamic_batcher_combines_requests_and_honors_max_batch():
    batches = []

    async def handler(items):
        batches.append(list(items))
        return [item * 2 for item in items]

    batcher = DynamicBatcher(handler, max_batch_size=3, max_wait_ms=10)
    await batcher.start()
    try:
        first, second = await asyncio.gather(
            batcher.submit([1, 2]),
            batcher.submit([3, 4]),
        )
        oversized = await batcher.submit([5, 6, 7, 8])
    finally:
        await batcher.close()

    assert first == [2, 4]
    assert second == [6, 8]
    assert oversized == [10, 12, 14, 16]
    assert all(len(batch) <= 3 for batch in batches)


# ---------------------------------------------------------------------------
# Evaluation → Path feedback loop tests
# ---------------------------------------------------------------------------


def _load_module_direct(rel_path: str, mocks: dict | None = None):
    """Load a module by filesystem path, bypassing __init__.py import chains.

    Provide `mocks` as a dict of {module_name: mock_object} to pre-seed
    sys.modules before loading, preventing heavy import chains.
    """
    import sys
    from unittest.mock import MagicMock

    target = Path(__file__).parents[1] / rel_path
    name = rel_path.replace("\\", "_").replace("/", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(name, target)
    module = importlib.util.module_from_spec(spec)

    saved = {}
    if mocks:
        for mod_name, mock_obj in mocks.items():
            saved[mod_name] = sys.modules.get(mod_name)
            sys.modules[mod_name] = mock_obj

    try:
        assert spec.loader is not None
        spec.loader.exec_module(module)
    finally:
        for mod_name, original in saved.items():
            if original is None:
                sys.modules.pop(mod_name, None)
            else:
                sys.modules[mod_name] = original

    return module


class TestEvalAgentNextActions:
    """EvalAgent._apply_strategies must produce traceable next_actions
    that differ materially between weak and strong scores."""

    @staticmethod
    def _make_agent():
        mod = _load_module_direct("app/agents/eval_agent.py")
        return mod.EvalAgent()

    def test_weak_scores_produce_remedial_actions(self):
        agent = self._make_agent()
        evaluation = {
            "scores": {
                "knowledge_mastery": 30,
                "learning_efficiency": 40,
                "engagement": 35,
                "consistency": 25,
                "improvement": 20,
            },
            "suggestions": [],
        }
        signals = agent._apply_strategies(evaluation, {})

        assert signals["difficulty_change"] == "easier"
        assert signals["review_suggested"] is True
        assert signals["adjust_pace"] is True
        assert signals.get("feynman_suggested") is True
        assert signals.get("recall_suggested") is True

        actions = signals.get("next_actions", [])
        action_names = {a["action"] for a in actions}
        assert "reduce_difficulty" in action_names
        assert "add_review_nodes" in action_names
        assert "apply_feynman_technique" in action_names
        assert "add_practice_nodes" in action_names
        assert "reduce_pace" in action_names

    def test_strong_scores_produce_advancement_actions(self):
        agent = self._make_agent()
        evaluation = {
            "scores": {
                "knowledge_mastery": 90,
                "learning_efficiency": 85,
                "engagement": 80,
                "consistency": 75,
                "improvement": 70,
            },
            "suggestions": [],
        }
        signals = agent._apply_strategies(evaluation, {})

        assert signals["difficulty_change"] == "harder"
        assert signals["review_suggested"] is False
        assert signals["adjust_pace"] is False
        assert signals.get("feynman_suggested") is not True
        assert signals.get("recall_suggested") is not True

        actions = signals.get("next_actions", [])
        action_names = {a["action"] for a in actions}
        assert "increase_difficulty" in action_names
        assert "reduce_difficulty" not in action_names
        assert "add_review_nodes" not in action_names
        assert "reduce_pace" not in action_names

    def test_moderate_scores_produce_review_only(self):
        agent = self._make_agent()
        evaluation = {
            "scores": {
                "knowledge_mastery": 55,
                "learning_efficiency": 60,
                "engagement": 65,
                "consistency": 60,
                "improvement": 50,
            },
            "suggestions": [],
        }
        signals = agent._apply_strategies(evaluation, {})

        assert signals["difficulty_change"] == "same"
        assert signals["review_suggested"] is True
        assert signals["adjust_pace"] is False

        actions = signals.get("next_actions", [])
        action_names = {a["action"] for a in actions}
        assert "add_review_nodes" in action_names
        assert "apply_feynman_technique" in action_names
        assert "reduce_difficulty" not in action_names
        assert "increase_difficulty" not in action_names


class TestPathAgentEvaluationContext:
    """PathAgent helpers must translate evaluation signals into
    prompt context and strategy adjustments."""

    @staticmethod
    def _load_path_agent():
        from unittest.mock import MagicMock

        mocks = {
            "app.agents": MagicMock(),
            "app.agents.resource_agent": MagicMock(),
            "app.agents.resource_agent.ResourceCoordinator": MagicMock(),
        }
        mod = _load_module_direct("app/agents/path_agent.py", mocks=mocks)
        return mod.PathAgent

    def test_build_context_empty_when_no_evaluation(self):
        PathAgent = self._load_path_agent()
        assert PathAgent._build_evaluation_context(None) == ""
        assert PathAgent._build_evaluation_context({}) == ""

    def test_build_context_includes_review_and_difficulty_for_weak(self):
        PathAgent = self._load_path_agent()
        evaluation = {
            "strategy_signals": {
                "review_suggested": True,
                "difficulty_change": "easier",
                "adjust_pace": True,
                "feynman_suggested": True,
                "next_actions": [
                    {"action": "reduce_difficulty", "reason": "low mastery"},
                    {"action": "add_review_nodes", "reason": "review needed"},
                ],
            }
        }
        ctx = PathAgent._build_evaluation_context(evaluation)

        assert "复习" in ctx
        assert "降低" in ctx or "easier" in ctx.lower()
        assert "放缓" in ctx or "减少" in ctx
        assert "费曼" in ctx
        assert "reduce_difficulty" in ctx
        assert "add_review_nodes" in ctx

    def test_build_context_suggests_advancement_for_strong(self):
        PathAgent = self._load_path_agent()
        evaluation = {
            "strategy_signals": {
                "review_suggested": False,
                "difficulty_change": "harder",
                "adjust_pace": False,
                "next_actions": [
                    {"action": "increase_difficulty", "reason": "high mastery"},
                ],
            }
        }
        ctx = PathAgent._build_evaluation_context(evaluation)

        assert "提高" in ctx or "挑战" in ctx or "harder" in ctx.lower()
        assert "increase_difficulty" in ctx
        assert "复习" not in ctx

    def test_apply_strategies_adds_review_when_suggested(self):
        PathAgent = self._load_path_agent()
        from app.services.learning_strategies import LearningStrategy

        base = [LearningStrategy.ELABORATION]
        evaluation = {
            "strategy_signals": {
                "review_suggested": True,
                "feynman_suggested": True,
                "recall_suggested": True,
            }
        }
        result = PathAgent._apply_evaluation_strategies(base, evaluation)

        assert LearningStrategy.SPACED_REPETITION in result
        assert LearningStrategy.FEYNMAN_TECHNIQUE in result
        assert LearningStrategy.ACTIVE_RECALL in result
        assert LearningStrategy.ELABORATION in result

    def test_apply_strategies_no_duplicates(self):
        PathAgent = self._load_path_agent()
        from app.services.learning_strategies import LearningStrategy

        base = [LearningStrategy.SPACED_REPETITION, LearningStrategy.FEYNMAN_TECHNIQUE]
        evaluation = {
            "strategy_signals": {
                "review_suggested": True,
                "feynman_suggested": True,
            }
        }
        result = PathAgent._apply_evaluation_strategies(base, evaluation)

        assert result.count(LearningStrategy.SPACED_REPETITION) == 1
        assert result.count(LearningStrategy.FEYNMAN_TECHNIQUE) == 1

    def test_apply_strategies_noop_when_no_evaluation(self):
        PathAgent = self._load_path_agent()
        from app.services.learning_strategies import LearningStrategy

        base = [LearningStrategy.ELABORATION]
        result = PathAgent._apply_evaluation_strategies(base, None)

        assert result == base
        assert result is not base  # returns a copy
