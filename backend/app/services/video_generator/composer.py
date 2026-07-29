# -*- coding: utf-8 -*-
"""Composer - uses FFmpeg to composite slides, audio, and character overlay into final video."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

from loguru import logger


FFMPEG_PATH = "C:/Program Files/File Converter/ffmpeg.exe"
OUTPUT_RESOLUTION = "1920x1080"
FPS = 30


def get_ffmpeg_path() -> str:
    return FFMPEG_PATH


async def compose_video(
    slide_paths: list[Path],
    audio_info: list[dict],
    character_png: Path,
    output_path: str | Path,
    slide_width: int = 1920,
    slide_height: int = 1080,
) -> Path:
    """Composite slides + audio + character overlay into final video.

    Args:
        slide_paths: List of PNG paths for each slide
        audio_info: List of dicts with audio_path and duration_seconds per slide
        character_png: Path to the Q版小老师 PNG (transparent background)
        output_path: Where to save the final MP4
        slide_width, slide_height: Slide dimensions

    Returns:
        Path to the generated video
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    work_dir = output_path.parent / f".work_{output_path.stem}"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        # --- Step 1: Create per-slide video clips with matching durations ---
        clip_paths = []
        for i, (slide_path, audio) in enumerate(zip(slide_paths, audio_info)):
            duration = audio.get("duration_seconds", 5.0)
            clip_path = work_dir / f"clip_{i:03d}.mp4"
            clip_paths.append(clip_path)

            cmd = [
                FFMPEG_PATH, "-y",
                "-loop", "1",
                "-i", str(slide_path),
                "-c:v", "libx264",
                "-t", f"{duration:.1f}",
                "-pix_fmt", "yuv420p",
                "-vf", f"scale={slide_width}:{slide_height}:force_original_aspect_ratio=decrease,pad={slide_width}:{slide_height}:(ow-iw)/2:(oh-ih)/2",
                "-r", str(FPS),
                "-an",
                str(clip_path),
            ]
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.wait()
            logger.debug(f"  clip {i}: {duration:.1f}s -> {clip_path.name}")

        # --- Step 2: Concatenate all clips with crossfade ---
        concat_path = work_dir / "concat_list.txt"
        with open(concat_path, "w") as f:
            for clip in clip_paths:
                f.write(f"file '{clip.resolve()}'\n")

        concat_video = work_dir / "concat.mp4"
        cmd = [
            FFMPEG_PATH, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_path),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(FPS),
            str(concat_video),
        ]
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()

        # --- Step 3: Add character overlay with floating animation ---
        char_w, char_h = _get_png_size(character_png)
        char_x = slide_width - char_w - 50
        char_y_base = slide_height - char_h - 30

        # Use FFmpeg drawtext filter to create a floating bob animation
        # The overlay filter with sin oscillation on Y position
        with_character = work_dir / "with_char.mp4"

        # Simple overlay with gentle bobbing: sin(time * freq) * amplitude
        # char_y = char_y_base + 5*sin(2*PI*t/2)
        overlay_filter = (
            f"overlay={char_x}:{char_y_base}+5*sin(2*PI*t/2)"
        )

        cmd = [
            FFMPEG_PATH, "-y",
            "-i", str(concat_video),
            "-i", str(character_png),
            "-filter_complex",
            f"[0:v][1:v]{overlay_filter}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "23",
            str(with_character),
        ]
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()

        video_with_char = with_character

        # --- Step 4: Mix audio tracks ---
        audio_paths = [a.get("audio_path") for a in audio_info if a.get("audio_path")]
        if audio_paths:
            mixed_audio = work_dir / "mixed_audio.mp3"
            await _mix_audios(audio_paths, mixed_audio)

            # --- Step 5: Final combine video + audio ---
            cmd = [
                FFMPEG_PATH, "-y",
                "-i", str(video_with_char),
                "-i", str(mixed_audio),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(output_path),
            ]
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.wait()
        else:
            cmd = [
                FFMPEG_PATH, "-y",
                "-i", str(video_with_char),
                "-c:v", "copy",
                str(output_path),
            ]
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.wait()

        logger.info(f"Video generated: {output_path}")
        return output_path

    finally:
        # Cleanup working files
        try:
            import shutil
            shutil.rmtree(work_dir)
        except Exception:
            pass


async def _mix_audios(audio_paths: list[str | Path], output_path: Path) -> Path:
    """Concatenate multiple audio files into one."""
    list_path = output_path.parent / "_audio_list.txt"
    with open(list_path, "w") as f:
        for p in audio_paths:
            resolved = Path(p).resolve()
            f.write(f"file '{resolved}'\n")

    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_path),
        "-c:a", "libmp3lame",
        "-q:a", "2",
        str(output_path),
    ]
    proc = await asyncio.create_subprocess_exec(*cmd)
    await proc.wait()
    list_path.unlink()
    return output_path


def _get_png_size(png_path: Path) -> tuple[int, int]:
    """Get PNG image dimensions."""
    from PIL import Image
    with Image.open(png_path) as img:
        return img.size
