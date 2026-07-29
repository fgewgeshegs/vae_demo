# -*- coding: utf-8 -*-
"""Video generation API routes - Agnes API integration."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.video_generator.generator import (
    generate_video,
    get_task,
    list_tasks,
    get_cached_video,
    VIDEO_OUTPUT_DIR,
)
from app.services.local_knowledge_base import LocalKnowledgeBase

router = APIRouter(tags=["视频生成"])


class GenerateRequest(BaseModel):
    topic: str
    content: str | None = None


class GenerateFromKPRequest(BaseModel):
    knowledge_point_title: str | None = None
    knowledge_point_id: int | None = None
    chapter_title: str | None = None
    topic: str | None = None
    content: str | None = None


@router.post("/videos/generate")
async def start_generation(req: GenerateFromKPRequest):
    """Start video generation task.

    If video is already cached for the knowledge_point_id, returns immediately.
    Otherwise, starts async generation via Agnes API.
    """
    # Check cache first
    if req.knowledge_point_id:
        cached = get_cached_video(req.knowledge_point_id)
        if cached:
            return {
                "task_id": f"cached_{req.knowledge_point_id}",
                "status": "completed",
                "message": "视频已缓存",
                "video_url": cached["video_url"],
            }

    task_id = f"video_{uuid.uuid4().hex[:12]}"

    # If no explicit content, try to fetch from knowledge base
    topic = req.topic or req.knowledge_point_title or req.chapter_title or "未命名"
    raw_content = req.content or ""

    if not raw_content and req.knowledge_point_title:
        try:
            kb = LocalKnowledgeBase()
            results = kb.search(req.knowledge_point_title, top_k=10)
            raw_content = "\n".join(
                r.get("content", "") or r.get("text", "")
                for r in results
                if (r.get("content") or r.get("text"))
            )
        except Exception:
            raw_content = f"关于 {req.knowledge_point_title} 的教学内容"

    if not raw_content:
        raw_content = f"关于 {topic} 的教学内容，这是自动生成的视频脚本素材。"

    # Start background task
    asyncio.create_task(
        generate_video(
            task_id=task_id,
            topic=topic,
            raw_content=raw_content,
            knowledge_point_id=req.knowledge_point_id,
        )
    )

    return {
        "task_id": task_id,
        "status": "queued",
        "message": "视频生成任务已启动，预计需要30秒-2分钟",
    }


@router.get("/videos/status/{task_id}")
async def get_generation_status(task_id: str):
    """Check video generation status."""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.get("/videos/list")
async def list_generated_videos():
    """List all generated videos."""
    tasks = list_tasks()
    completed = [t for t in tasks if t.get("status") == "completed"]
    return {"total": len(tasks), "completed": len(completed), "tasks": tasks}


@router.get("/uploads/videos/{filename}")
async def stream_video(filename: str):
    """Stream a generated video file."""
    video_path = VIDEO_OUTPUT_DIR / filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="视频文件不存在")
    return FileResponse(str(video_path), media_type="video/mp4")
