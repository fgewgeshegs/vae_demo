from app.models.learning_run import (
    AssessmentAttempt,
    AssessmentItemResult,
    ChapterLearningRun,
    ChapterLearningStage,
    KnowledgePointDependency,
    KnowledgePointMastery,
    MasteryHistory,
    PracticeAttempt,
)
from app.services.learning_loop import PASS_THRESHOLD, STAGES, feedback_for_mastery


def test_learning_loop_has_separate_persistent_concerns():
    assert ChapterLearningRun.__tablename__ == "chapter_learning_runs"
    assert ChapterLearningStage.__tablename__ == "chapter_learning_stages"
    assert KnowledgePointMastery.__tablename__ == "knowledge_point_mastery"
    assert MasteryHistory.__tablename__ == "mastery_history"
    assert PracticeAttempt.__tablename__ == "practice_attempts"
    assert AssessmentAttempt.__tablename__ == "assessment_attempts"
    assert AssessmentItemResult.__tablename__ == "assessment_item_results"
    assert KnowledgePointDependency.__tablename__ == "knowledge_point_dependencies"
    assert STAGES == ("learn", "practice", "assess", "feedback", "review", "remedial")


def test_feedback_routes_weak_mastery_to_remedial():
    feedback = feedback_for_mastery({1: PASS_THRESHOLD, 2: 0.45})
    assert feedback["result"] == "partial_mastery"
    assert feedback["next_action"]["type"] == "remedial"
    assert feedback["mastered"] == [{"knowledge_point_id": 1, "mastery": PASS_THRESHOLD}]
    assert feedback["weak"] == [{"knowledge_point_id": 2, "mastery": 0.45}]


def test_feedback_routes_full_mastery_to_review():
    feedback = feedback_for_mastery({1: 0.8, 2: 1.0})
    assert feedback["result"] == "mastered"
    assert feedback["weak"] == []
    assert feedback["next_action"]["type"] == "review"
