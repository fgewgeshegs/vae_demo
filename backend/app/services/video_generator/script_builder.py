# -*- coding: utf-8 -*-
"""Script builder - uses LLM to organize knowledge base content into a video script."""

from __future__ import annotations

import json
from typing import Any

from loguru import logger
from app.core.llm_gateway import get_llm_gateway


SCRIPT_SYSTEM_PROMPT = """你是一位教学视频的脚本书写专家。你的任务是将给定的教学内容组织成一个5-8分钟的教学视频脚本，深入讲解知识点的重点和难点。

你必须严格按照以下 JSON 格式输出（只输出 JSON，不要其他文字）：

{
  "title": "视频标题（提炼核心主题，15字以内）",
  "slides": [
    {
      "title": "本页标题（10字以内）",
      "content": "本页详细讲解内容（80-150字，用于幻灯片显示，要包含关键概念和解释）",
      "bullets": ["要点1", "要点2", "要点3", "要点4"],
      "narration": "讲师口头讲解词（100-200字，自然口语化，要有教学节奏感，可适当举例说明）"
    }
  ]
}

要求：
1. 总共12-18页幻灯片，每页对应视频中20-30秒的讲解
2. 开篇1-2页做引入和概述，结尾1-2页做总结和回顾
3. 中间内容要层层递进，每个要点都要展开讲解，不要只是罗列
4. content 字段用于幻灯片上展示的核心文字
5. narration 字段是讲师说的口语化讲解，要像真人老师讲课一样，有解释、有举例、有互动感
6. 所有文字使用中文
7. 确保输出是合法的 JSON"""


async def build_script(topic: str, raw_content: str) -> dict[str, Any]:
    gateway = get_llm_gateway()
    user_message = f"教学主题：{topic}\n\n教学内容素材：\n{raw_content[:8000]}\n\n请根据上述素材生成一个5-8分钟的教学视频脚本，深入讲解核心概念和重点内容。"

    try:
        response = await gateway.chat(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=SCRIPT_SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=4096,
        )
        text = response.content.strip()
        if "`json" in text:
            text = text.split("`json")[1].split("`")[0].strip()
        elif "`" in text:
            text = text.split("`")[1].split("`")[0].strip()
        script = json.loads(text)
        logger.info(f"Script built: {script.get('title', 'unknown')} ({len(script.get('slides', []))} slides)")
        return script
    except Exception as e:
        logger.error(f"Failed to build script: {e}")
        return _fallback_script(topic, raw_content)


def _fallback_script(topic: str, raw_content: str) -> dict[str, Any]:
    lines = [l.strip() for l in raw_content.split(chr(10)) if l.strip()]
    chunk_size = max(1, len(lines) // 3)
    slides = []
    for i in range(0, min(len(lines), 3 * chunk_size), chunk_size):
        chunk = lines[i:i + chunk_size]
        text = chr(10).join(chunk)
        slides.append({
            "title": f"第{i // chunk_size + 1}部分",
            "content": text[:200],
            "bullets": [l[:40] for l in chunk[:4]],
            "narration": f"接下来我们学习：{text[:100]}",
        })
    if not slides:
        slides.append({
            "title": topic[:10],
            "content": raw_content[:200],
            "bullets": [raw_content[:40]],
            "narration": f"大家好，今天我们来学习{topic}。{raw_content[:100]}",
        })
    return {"title": topic[:15], "slides": slides}
