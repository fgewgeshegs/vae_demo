"""Regenerate shared resources using DeepSeek grounded in textbook content from chunks.json."""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select, func
from loguru import logger

from app.core.database import async_session_factory
from app.core.llm_gateway import LLMGateway, LLMMessage
from app.models.knowledge_point import KnowledgePoint
from app.models.learning_resource import LearningResource
from app.models.course import Chapter
from app.services.event_service import EventService, EventType

SHARED_USER_ID = 1
COURSE_ID = 1
CHUNKS_PATH = r"D:\jay_demo\knowledge-base\chunks\chunks.json"

RESOURCE_AGENTS = [
    ("document", "课程讲义", "你是一位专业的课程讲师。请根据提供的教材内容，生成一份高质量的Markdown格式的结构化讲义。要求：1) 包含概念解释、原理说明、实际应用 2) 使用标题层级组织内容 3) 加入思考题。讲义必须基于提供的教材内容，不能凭空编造。请使用中文。"),
    ("mindmap", "思维导图", "你是一位思维导图设计师。请根据提供的教材内容，生成Mermaid语法格式的思维导图。要求：1) 使用Mermaid mindmap语法 2) 包含主题、子主题和关键概念 3) 层级清晰，便于记忆。思维导图必须基于提供的教材内容。只返回Mermaid代码块。"),
    ("exercise", "练习题", "你是一位出题专家。请根据提供的教材内容，生成高质量的练习题。要求：1) 包含选择题、填空题、简答题 2) 难度递进（从易到难）3) 附参考答案和解析 4) 5-10题。练习题必须基于教材中的实际知识点。使用中文。"),
    ("code", "代码案例", "你是一位编程导师。请根据提供的教材内容，生成完整可运行的Python代码示例。要求：1) 包含完整可运行的代码 2) 添加中文注释说明关键步骤 3) 包含输入输出示例 4) 代码风格规范整洁。代码示例必须基于教材中提到的算法或概念。"),
    ("reading", "拓展阅读", "你是一位学术阅读导师。请根据提供的教材内容，生成拓展阅读材料。要求：1) 推荐相关的论文/文章/书籍 2) 提供每篇材料的核心观点摘要 3) 说明与当前学习内容的关联 4) 标注优先级和预计阅读时间。拓展阅读必须与教材内容相关。使用中文。"),
    ("video", "教学脚本", "你是一位教学动画脚本作者。请根据提供的教材内容，生成教学动画脚本。要求：1) 包含场景描述和旁白文本 2) 适合生成教学动画 3) 时长控制在3-5分钟 4) 包含关键概念的可视化说明。脚本必须基于教材内容。使用中文。"),
]

with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    ALL_CHUNKS = json.load(f)


def extract_keywords(text: str) -> set[str]:
    words = re.findall(r"[\w\u4e00-\u9fff]+", text)
    stop_words = {"的", "与", "和", "了", "在", "是", "有", "为", "等", "之", "及", "或", "方法", "技术"}
    return {w for w in words if len(w) >= 2 and w not in stop_words}


def find_relevant_chunks(kp_title: str, top_k: int = 5) -> list[str]:
    keywords = extract_keywords(kp_title)
    if not keywords:
        return []
    scored = []
    for chunk in ALL_CHUNKS:
        text = chunk.get("text", "")
        title = chunk.get("title", "")
        combined = title + " " + text
        score = sum(1 for kw in keywords if kw in combined)
        title_score = sum(2 for kw in keywords if kw in title)
        total = score + title_score
        if total > 0:
            scored.append((total, text[:2000], title))
    scored.sort(key=lambda x: -x[0])
    return [f"[教材节选 - {t}]:\n{s}" for _, s, t in scored[:top_k]]


async def get_incomplete_kps() -> list:
    async with async_session_factory() as db:
        all_kps = (await db.execute(
            select(KnowledgePoint).join(Chapter).where(Chapter.course_id == COURSE_ID)
            .order_by(Chapter.sort_order, KnowledgePoint.sort_order)
        )).scalars().all()
        incomplete = []
        for kp in all_kps:
            count = (await db.execute(
                select(func.count(LearningResource.id)).where(
                    LearningResource.knowledge_point_id == kp.id,
                    LearningResource.user_id == SHARED_USER_ID
                )
            )).scalar()
            if not count or count < 6:
                incomplete.append(kp)
        return incomplete


async def generate_resource(llm: LLMGateway, kp_title: str, textbook_context: str, rtype: str, rlabel: str, sys_prompt: str) -> dict:
    context_block = f"## 教材参考内容\n\n{textbook_context}" if textbook_context else "教材中未找到与知识点直接相关的内容。请基于你的专业知识生成，但必须明确标注为补充内容。"
    user_prompt = (
        f"## 知识点：{kp_title}\n\n"
        f"{context_block}\n\n"
        f"## 任务\n\n请根据上面的教材内容，生成一份{rlabel}（{rtype}类型）。\n"
        f"内容必须基于教材，不能脱离教材凭空编造。\n"
        f"如果教材内容不足以覆盖该知识点，可以适当补充说明，但必须标明哪些是教材原文、哪些是补充内容。\n请直接输出完整内容，不要额外解释。"
    )
    response = await llm.chat(
        messages=[LLMMessage("user", user_prompt)],
        system_prompt=sys_prompt,
        temperature=0.7, max_tokens=4096,
    )
    return {"title": f"{kp_title} - {rlabel}", "content": response.content, "type": rtype}


async def save_resource(kp: KnowledgePoint, result: dict, rtype: str) -> bool:
    try:
        async with async_session_factory() as db:
            resource = LearningResource(
                user_id=SHARED_USER_ID, course_id=COURSE_ID, chapter_id=kp.chapter_id,
                knowledge_point_id=kp.id, resource_type=rtype,
                title=result["title"], content=result["content"],
                resource_metadata={
                    "knowledge_point": kp.title, "knowledge_point_id": kp.id,
                    "shared_resource": True, "generated_by": "DeepSeek",
                    "grounded_in_textbook": True,
                }, is_generated=True,
            )
            db.add(resource)
            await db.commit()
            await db.refresh(resource)
        await EventService.emit(user_id=SHARED_USER_ID, course_id=COURSE_ID,
            event_type=EventType.RESOURCE_GENERATED, source_agent=f"DeepSeek-{rtype}Agent",
            target_type="learning_resource", target_id=resource.id,
            payload={"resource_type": rtype, "knowledge_point_id": kp.id})
        return True
    except Exception as exc:
        logger.error(f"Save failed for {kp.title}/{rtype}: {exc}")
        return False


async def main() -> None:
    logger.info("=== Finding incomplete KPs ===")
    incomplete = await get_incomplete_kps()
    logger.info(f"Incomplete KPs: {len(incomplete)}")
    
    if not incomplete:
        logger.info("All KPs complete! Nothing to do.")
        return
    
    llm = LLMGateway()
    total_ok, total_fail = 0, 0
    
    for index, kp in enumerate(incomplete, start=1):
        logger.info(f"[{index}/{len(incomplete)}] KP[{kp.id}]: {kp.title}")
        relevant = find_relevant_chunks(kp.title)
        ctx = "\n\n".join(relevant) if relevant else ""
        logger.info(f"  Found {len(relevant)} relevant chunks")
        
        tasks = [generate_resource(llm, kp.title, ctx, r, l, s) for r, l, s in RESOURCE_AGENTS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"  X {RESOURCE_AGENTS[i][0]} failed: {res}")
                total_fail += 1
                continue
            ok = await save_resource(kp, res, RESOURCE_AGENTS[i][0])
            if ok:
                total_ok += 1
            else:
                total_fail += 1
    
    logger.info(f"Done! Generated: {total_ok}, Failed: {total_fail}")


if __name__ == "__main__":
    asyncio.run(main())
