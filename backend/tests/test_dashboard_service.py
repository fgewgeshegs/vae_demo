from types import SimpleNamespace

from app.services.dashboard_service import build_recommendation, select_current_node


def test_select_current_node_uses_active_fallback_when_index_is_invalid():
    nodes = [
        {"id": "done", "status": "completed"},
        {"id": "active", "status": "in_progress"},
        {"id": "next", "status": "pending"},
    ]
    index, node = select_current_node(nodes, 99)
    assert index == 1
    assert node["id"] == "active"


def test_select_current_node_skips_completed_index():
    nodes = [
        {"id": "done", "status": "completed"},
        {"id": "next", "status": "pending"},
    ]
    index, node = select_current_node(nodes, 0)
    assert index == 1
    assert node["id"] == "next"


def test_recommendation_only_uses_recorded_evidence():
    profile = SimpleNamespace(
        version=3,
        profile_data={
            "knowledge_gaps": ["启发式函数"],
            "weak_points": [],
            "learning_pace": {"preferred_session_minutes": 25},
        },
    )
    evaluation = SimpleNamespace(strategy_signals={"review_first": "先复习核心概念"})
    result = build_recommendation(profile, evaluation, {"title": "启发式函数", "estimated_minutes": 20})
    assert result is not None
    assert [reason["kind"] for reason in result["reasons"]] == ["knowledge_gap", "evaluation_signal", "learning_pace"]


def test_recommendation_is_empty_without_matching_evidence():
    profile = SimpleNamespace(version=1, profile_data={"knowledge_gaps": ["线性代数"], "weak_points": []})
    assert build_recommendation(profile, None, {"title": "A* 搜索", "estimated_minutes": 10}) is None
