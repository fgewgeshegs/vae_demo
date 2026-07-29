# -*- coding: utf-8 -*-
"""TTS module - uses Edge TTS for Chinese speech generation."""

from __future__ import annotations

import asyncio
import edge_tts
from pathlib import Path


TTS_VOICE = "zh-CN-XiaoxiaoNeural"

async def generate_tts(text: str, output_path: str | Path, voice: str = TTS_VOICE) -> Path:
    """Generate TTS audio from text using Edge TTS.

    Args:
        text: Text to convert to speech
        output_path: Path to save the audio file (.mp3 or .wav)
        voice: TTS voice name (default: zh-CN-XiaoxiaoNeural)

    Returns:
        Path to the generated audio file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))

    return output_path


async def generate_slide_audios(
    slides: list[dict],
    output_dir: str | Path,
    voice: str = TTS_VOICE,
) -> list[dict]:
    """Generate TTS audio for each slide's narration.

    Args:
        slides: List of slide dicts with 'narration' field
        output_dir: Directory to save audio files
        voice: TTS voice name

    Returns:
        List of dicts: {slide_index, audio_path, duration_seconds}
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, slide in enumerate(slides):
        narration = slide.get("narration", "")
        if not narration:
            results.append({
                "slide_index": i,
                "audio_path": None,
                "duration_seconds": 5.0,
            })
            continue

        audio_path = output_dir / f"slide_{i:03d}.mp3"
        await generate_tts(narration, audio_path, voice)

        # Get audio duration using ffprobe
        duration = await _get_audio_duration(audio_path)
        duration = max(duration, 5.0)

        results.append({
            "slide_index": i,
            "audio_path": str(audio_path),
            "duration_seconds": duration,
        })

    return results


async def generate_full_audio(
    full_narration: str,
    output_path: str | Path,
    voice: str = TTS_VOICE,
) -> tuple[Path, float]:
    """Generate one continuous TTS audio for the entire script.

    Returns:
        (audio_path, duration_seconds)
    """
    audio_path = await generate_tts(full_narration, output_path, voice)
    duration = await _get_audio_duration(audio_path)
    return audio_path, duration


async def _get_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds using ffprobe."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return float(stdout.decode().strip())
    except Exception:
        # Fallback: estimate based on character count (roughly 4 chars/sec for Chinese)
        import os
        size = os.path.getsize(audio_path)
        if size < 1000:
            return 3.0
        return size / 16000 * 2
