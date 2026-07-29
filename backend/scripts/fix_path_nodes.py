"""Fix study path nodes to reference correct knowledge_point_ids (with proper JSON mutation tracking)."""

from __future__ import annotations
import asyncio, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from app.core.database import async_session_factory
from app.models.knowledge_point import KnowledgePoint
from app.models.study_path import StudyPath
from app.models.course import Chapter

STOP_WORDS = {"的", "与", "和", "了", "在", "是", "有", "为", "等", "之", "及", "或", "方法", "技术", "学习", "综合", "复习", "实践", "练习", "课程"}

def extract_keywords(text):
    words = re.findall(r"[\w\u4e00-\u9fff]+", text)
    return {w for w in words if len(w) >= 2 and w not in STOP_WORDS}

def match_kp(title, kps):
    keywords = extract_keywords(title)
    if not keywords:
        return None
    best_score, best_kp = 0, None
    for kp in kps:
        kp_keywords = extract_keywords(kp.title)
        if not kp_keywords:
            continue
        overlap = len(keywords & kp_keywords)
        t_low, k_low = title.lower(), kp.title.lower()
        bonus = 3 if k_low in t_low or t_low in k_low else 0
        score = overlap + bonus
        if score > best_score:
            best_score, best_kp = score, kp
    return best_kp if best_score > 0 else None

async def main():
    async with async_session_factory() as db:
        kps = (await db.execute(
            select(KnowledgePoint).join(Chapter).where(Chapter.course_id == 1)
            .order_by(Chapter.sort_order, KnowledgePoint.sort_order)
        )).scalars().all()
        print("Loaded", len(kps), "knowledge points")
        
        paths = (await db.execute(select(StudyPath))).scalars().all()
        print("Total paths:", len(paths))
        
        for path in paths:
            nodes = path.path_data.get("nodes", [])
            changes = 0
            for i, node in enumerate(nodes):
                node_id = node.get("id")
                # Set node id if missing
                if not node_id:
                    nodes[i]["id"] = f"node-{i + 1}"
                    changes += 1
                
                # Set knowledge_point_id if missing
                if not node.get("knowledge_point_id"):
                    matched = match_kp(node.get("title", ""), kps)
                    if matched:
                        nodes[i]["knowledge_point_id"] = matched.id
                        nodes[i]["chapter_id"] = matched.chapter_id
                        if not node.get("learning_content") and matched.content:
                            nodes[i]["learning_content"] = matched.content
                        changes += 1
            
            if changes > 0:
                path.path_data = dict(path.path_data)
                path.path_data["nodes"] = nodes
                # CRITICAL: Flag the JSON column as modified for SQLAlchemy to track
                flag_modified(path, "path_data")
                print("Path[" + str(path.id) + "] user=" + str(path.user_id) + ": fixed " + str(changes) + " nodes")
            else:
                print("Path[" + str(path.id) + "] user=" + str(path.user_id) + ": no changes")
        
        await db.commit()
        print("\nDone! All changes committed.")

asyncio.run(main())
