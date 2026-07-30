import json
from pathlib import Path

from app.agents.path_agent import PathAgent
from scripts.sync_textbook_course import learning_sections


def test_full_course_path_covers_every_textbook_leaf_section():
    tree_path = Path(__file__).resolve().parents[3] / "textbook_course_tree_v2.json"
    textbook_chapters = json.loads(tree_path.read_text(encoding="utf-8"))["course"]["chapters"]

    next_kp_id = 1
    course_context = {"chapters": []}
    expected_kp_ids = set()
    for chapter_id, chapter in enumerate(textbook_chapters, start=1):
        knowledge_points = []
        for section in learning_sections(chapter["knowledge_points"]):
            knowledge_points.append(
                {
                    "id": next_kp_id,
                    "title": section["title"],
                    "difficulty": "medium",
                    "content": None,
                }
            )
            expected_kp_ids.add(next_kp_id)
            next_kp_id += 1
        course_context["chapters"].append(
            {"id": chapter_id, "title": chapter["title"], "knowledge_points": knowledge_points}
        )

    nodes = PathAgent._build_full_course_nodes(course_context, {"knowledge_base": {"level": "beginner"}})
    learning_nodes = [node for node in nodes if node["coverage_role"] == "knowledge_point"]

    assert {node["knowledge_point_id"] for node in learning_nodes} == expected_kp_ids
    assert {node["chapter_id"] for node in learning_nodes} == set(range(1, 16))
    assert len([node for node in nodes if node["coverage_role"] == "chapter_preview"]) == 15
    assert len([node for node in nodes if node["coverage_role"] == "chapter_review"]) == 15
