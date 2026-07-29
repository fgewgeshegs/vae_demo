# -*- coding: utf-8 -*-
"""Video generation orchestrator - Agnes API integration."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

from loguru import logger

from .agnes_api import generate_with_agnes
from .script_builder import build_script


VIDEO_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "uploads" / "videos"


# In-memory task tracking
_tasks: dict[str, dict] = {}


def get_task(task_id: str) -> Optional[dict]:
    return _tasks.get(task_id)


def list_tasks() -> list[dict]:
    return [
        {"task_id": tid, **t}
        for tid, t in _tasks.items()
    ]


def get_cached_video(knowledge_point_id: int) -> Optional[dict]:
    """Check if a video is already cached for a knowledge point."""
    cache_filename = f"kp_{knowledge_point_id}.mp4"
    cache_path = VIDEO_OUTPUT_DIR / cache_filename
    if cache_path.exists():
        return {
            "video_path": str(cache_path),
            "video_url": f"/api/v1/uploads/videos/{cache_filename}",
        }
    return None


async def generate_video(
    task_id: str,
    topic: str,
    raw_content: str,
    knowledge_point_id: Optional[int] = None,
) -> dict:
    """Full video generation pipeline using Agnes API.

    Args:
        task_id: Unique task ID for tracking
        topic: Topic title
        raw_content: Raw text content from knowledge base
        knowledge_point_id: Optional KP ID for caching

    Returns:
        Task result dict
    """
    result = {
        "task_id": task_id,
        "status": "processing",
        "progress": 0,
        "video_path": None,
        "video_url": None,
        "title": topic,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "knowledge_point_id": knowledge_point_id,
    }
    _tasks[task_id] = result

    try:
        # Step 1: Build prompt from content
        result["progress"] = 10
        _tasks[task_id] = result.copy()

        logger.info(f"[{task_id}] Building prompt for: {topic}")
        script = await build_script(topic, raw_content)
        slides = script.get("slides", [])

        # Build a consolidated prompt for Agnes from the script
        prompt_parts = [f"教学视频：{script.get('title', topic)}"]
        max_slides = min(len(slides), 15)  # Process up to 15 slides
        for i, slide in enumerate(slides[:max_slides], 1):
            slide_title = slide.get("title", "")
            bullets = slide.get("bullets", [])
            narration = slide.get("narration", "")
            if slide_title:
                prompt_parts.append(f"第{i}部分：{slide_title}")
            if narration:
                prompt_parts.append(narration[:300])  # Longer narration per slide

        agnes_prompt = "\n".join(prompt_parts)
        # Allow longer prompt for longer videos
        if len(agnes_prompt) > 4000:
            agnes_prompt = agnes_prompt[:4000]

        result["progress"] = 25
        result["title"] = script.get("title", topic)
        _tasks[task_id] = result.copy()

        # Step 2: Determine output path
        if knowledge_point_id:
            video_filename = f"kp_{knowledge_point_id}.mp4"
        else:
            video_filename = f"{task_id}.mp4"

        video_path = VIDEO_OUTPUT_DIR / video_filename
        VIDEO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Step 3: Call Agnes API
        logger.info(f"[{task_id}] Calling Agnes API...")
        result["progress"] = 30
        _tasks[task_id] = result.copy()

        # Agnes polling happens inside generate_with_agnes
        # We'll update progress based on estimated time
        await generate_with_agnes(
            prompt=agnes_prompt,
            save_path=video_path,
        )

        result["progress"] = 100
        result["status"] = "completed"
        result["video_path"] = str(video_path)
        result["video_url"] = f"/api/v1/uploads/videos/{video_filename}"
        result["completed_at"] = datetime.now().isoformat()
        _tasks[task_id] = result.copy()

        logger.info(f"[{task_id}] Video generated: {video_path}")
        return result

    except Exception as e:
        logger.error(f"[{task_id}] Video generation failed: {e}")
        result["status"] = "failed"
        result["error"] = str(e)
        result["progress"] = 0
        _tasks[task_id] = result.copy()
        return result
