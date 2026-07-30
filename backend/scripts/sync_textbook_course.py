"""Synchronise the 15-chapter textbook tree into the runtime course database.

The operation is idempotent. It creates or updates a dedicated textbook course
and leaves the previous nine-chapter demo course and its learner history intact.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select, update

from app.core.database import async_session_factory
from app.models.course import Chapter, Course
from app.models.knowledge_point import KnowledgePoint


COURSE_TITLE = "人工智能导论（教材版）"
TREE_PATH = Path(__file__).resolve().parents[3] / "textbook_course_tree_v2.json"


def learning_sections(points: list[dict]) -> list[dict]:
    """Return only leaf learning sections; group and review nodes are excluded."""
    result: list[dict] = []
    for point in points:
        children = point.get("children") or []
        if children:
            result.extend(learning_sections(children))
        elif point.get("resource_target"):
            result.append(point)
    return result


async def main() -> None:
    tree = json.loads(TREE_PATH.read_text(encoding="utf-8"))
    chapters = tree["course"]["chapters"]
    expected_sections = sum(len(learning_sections(chapter["knowledge_points"])) for chapter in chapters)

    async with async_session_factory() as session:
        course = (
            await session.execute(select(Course).where(Course.title == COURSE_TITLE))
        ).scalar_one_or_none()
        if not course:
            course = Course(
                title=COURSE_TITLE,
                description="基于《人工智能导论》教材目录的完整 15 章课程。",
                seed_course=True,
                is_active=True,
            )
            session.add(course)
            await session.flush()
        else:
            course.description = "基于《人工智能导论》教材目录的完整 15 章课程。"
            course.seed_course = True
            course.is_active = True

        # Only one course should be selected when no explicit course_id is passed.
        await session.execute(
            update(Course)
            .where(Course.id != course.id, Course.seed_course.is_(True))
            .values(seed_course=False)
        )

        existing_chapters = {
            chapter.sort_order: chapter
            for chapter in (
                await session.execute(select(Chapter).where(Chapter.course_id == course.id))
            ).scalars()
        }
        imported_sections = 0
        for chapter_data in chapters:
            sort_order = chapter_data["sort_order"]
            chapter = existing_chapters.get(sort_order)
            if not chapter:
                chapter = Chapter(course_id=course.id, title=chapter_data["title"], sort_order=sort_order)
                session.add(chapter)
                await session.flush()
            else:
                chapter.title = chapter_data["title"]

            sections = learning_sections(chapter_data["knowledge_points"])
            existing_points = {
                point.sort_order: point
                for point in (
                    await session.execute(
                        select(KnowledgePoint).where(KnowledgePoint.chapter_id == chapter.id)
                    )
                ).scalars()
            }
            for section_index, section in enumerate(sections, start=1):
                point = existing_points.get(section_index)
                if not point:
                    point = KnowledgePoint(
                        chapter_id=chapter.id,
                        title=section["title"],
                        content=None,
                        difficulty="medium",
                        prerequisites=[],
                        sort_order=section_index,
                    )
                    session.add(point)
                else:
                    point.title = section["title"]
                    point.sort_order = section_index
                imported_sections += 1

        await session.commit()
        print(
            f"Synced course_id={course.id}; chapters={len(chapters)}; "
            f"leaf_sections={imported_sections}/{expected_sections}."
        )


if __name__ == "__main__":
    asyncio.run(main())
