# -*- coding: utf-8 -*-
"""Agnes Video V2.0 API client - text-to-video generation."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from app.core.config import settings


AGNES_BASE = settings.AGNES_API_BASE
AGNES_API_KEY = settings.AGNES_API_KEY

# Default video parameters
DEFAULT_WIDTH = 1152
DEFAULT_HEIGHT = 768
DEFAULT_FRAMES = 121  # ~5 seconds at 24fps
DEFAULT_FPS = 24
POLL_INTERVAL = 5  # seconds
MAX_POLL_ATTEMPTS = 60  # 5 minutes max


async def create_video_task(
    prompt: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    num_frames: int = DEFAULT_FRAMES,
    frame_rate: int = DEFAULT_FPS,
) -> dict:
    """Submit a video generation task to Agnes API.

    Returns:
        dict with keys: task_id, video_id, status, ...
    """
    if not AGNES_API_KEY:
        raise ValueError("AGNES_API_KEY not configured. Set it in .env file.")

    payload = {
        "model": "agnes-video-v2.0",
        "prompt": prompt,
        "width": width,
        "height": height,
        "num_frames": num_frames,
        "frame_rate": frame_rate,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{AGNES_BASE}/v1/videos",
            headers={
                "Authorization": f"Bearer {AGNES_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        logger.info(
            f"Agnes task created: task_id={data.get('task_id')}, "
            f"video_id={data.get('video_id')}, status={data.get('status')}"
        )
        return data


async def poll_video_status(
    video_id: str,
    max_attempts: int = MAX_POLL_ATTEMPTS,
) -> dict:
    """Poll Agnes API until video generation completes.

    Returns:
        dict with keys: status, url (when completed), error (when failed)
    """
    if not AGNES_API_KEY:
        raise ValueError("AGNES_API_KEY not configured.")

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(max_attempts):
            resp = await client.get(
                f"{AGNES_BASE}/agnesapi",
                params={"video_id": video_id},
                headers={"Authorization": f"Bearer {AGNES_API_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()

            status = data.get("status", "unknown")
            progress = data.get("progress", 0)

            logger.debug(
                f"Agnes poll [{attempt+1}/{max_attempts}]: "
                f"video_id={video_id}, status={status}, progress={progress}%"
            )

            if status == "completed":
                logger.info(f"Agnes video completed: {video_id}, url={data.get('url')}")
                return data
            elif status == "failed":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Agnes video failed: {video_id}, error={error_msg}")
                return {"status": "failed", "error": error_msg}

            await asyncio.sleep(POLL_INTERVAL)

        raise TimeoutError(f"Agnes video generation timed out after {max_attempts * POLL_INTERVAL}s")


async def download_video(url: str, save_path: Path) -> Path:
    """Download video from Agnes URL to local path.

    Args:
        url: Temporary video URL from Agnes
        save_path: Local path to save the video

    Returns:
        Path to saved video file
    """
    save_path.parent.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()

        save_path.write_bytes(resp.content)
        logger.info(f"Video downloaded: {save_path} ({save_path.stat().st_size} bytes)")

        return save_path


async def generate_with_agnes(
    prompt: str,
    save_path: Path,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    num_frames: int = DEFAULT_FRAMES,
    frame_rate: int = DEFAULT_FPS,
) -> Path:
    """Full Agnes pipeline: create task → poll → download.

    Args:
        prompt: Video generation prompt
        save_path: Where to save the final video
        width/height/resolution params

    Returns:
        Path to saved video

    Raises:
        ValueError: If API key not configured
        TimeoutError: If generation takes too long
        httpx.HTTPStatusError: If API returns error
    """
    # Step 1: Create task
    task_data = await create_video_task(
        prompt=prompt,
        width=width,
        height=height,
        num_frames=num_frames,
        frame_rate=frame_rate,
    )

    video_id = task_data.get("video_id")
    if not video_id:
        raise ValueError(f"No video_id in response: {task_data}")

    # Step 2: Poll until complete
    result = await poll_video_status(video_id)

    if result.get("status") != "completed":
        raise RuntimeError(f"Video generation failed: {result.get('error')}")

    video_url = result.get("url")
    if not video_url:
        raise ValueError("No URL in completed response")

    # Step 3: Download
    return await download_video(video_url, save_path)
