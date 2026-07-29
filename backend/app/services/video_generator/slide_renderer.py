# -*- coding: utf-8 -*-
"""Slide renderer - renders whiteboard-style slides as PNG images using Pillow."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


# Slide dimensions (16:9)
SLIDE_WIDTH = 1920
SLIDE_HEIGHT = 1080

# Colors
WHITE = (255, 255, 255)
BLACK = (10, 10, 10)
GRAY = (100, 100, 100)
LIGHT_GRAY = (240, 240, 240)
ACCENT_BLUE = (41, 98, 255)
ACCENT_GREEN = (0, 180, 100)
BORDER_COLOR = (220, 220, 220)

FONT_PATHS = [
    "C:/Windows/Fonts/SIMHEI.TTF",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
]


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.replace(chr(10), " \n ").split()
    lines = []
    current = []
    for word in words:
        if word == "\n":
            lines.append(" ".join(current))
            current = []
            continue
        current.append(word)
        line = " ".join(current)
        bb = font.getbbox(line)
        w = bb[2] - bb[0]
        if w > max_width:
            current.pop()
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    if not lines:
        lines = [text]
    return lines


def render_slide(
    slide: dict,
    output_path: str | Path,
    slide_number: int = 0,
    total_slides: int = 1,
    width: int = SLIDE_WIDTH,
    height: int = SLIDE_HEIGHT,
) -> Path:
    """Render a single slide as a PNG image.

    Args:
        slide: Dict with title, content, bullets keys
        output_path: Where to save the PNG
        slide_number: Current slide index (for page number)
        total_slides: Total number of slides

    Returns:
        Path to the rendered PNG
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(img)

    # Fonts
    title_font = _get_font(56, bold=True)
    subtitle_font = _get_font(36, bold=False)
    body_font = _get_font(32)
    bullet_font = _get_font(30)

    margins = 80
    content_width = width - 2 * margins

    # --- Header line ---
    draw.rectangle([(margins, 60), (width - margins, 62)], fill=ACCENT_BLUE)

    # --- Title ---
    title = slide.get("title", "")
    draw.text((margins, 90), title, fill=BLACK, font=title_font)

    # --- Content / Bullets ---
    content = slide.get("content", "")
    bullets = slide.get("bullets", [])
    y_start = 200
    y = y_start

    if bullets:
        for i, bullet in enumerate(bullets[:6]):
            text = f"{chr(8226)} {bullet}"
            lines = _wrap_text(text, bullet_font, content_width - 80)
            for line in lines:
                draw.text((margins + 40, y), line, fill=BLACK, font=bullet_font)
                y += bullet_font.getbbox(line)[3] - bullet_font.getbbox(line)[1] + 8
            if y > height - 120:
                break
        y += 20

    if content and not bullets:
        lines = _wrap_text(content, body_font, content_width)
        for line in lines:
            draw.text((margins, y), line, fill=GRAY, font=body_font)
            bb = body_font.getbbox(line)
            y += bb[3] - bb[1] + 6
            if y > height - 120:
                break

    # --- Bottom bar ---
    draw.rectangle([(0, height - 70), (width, height - 68)], fill=LIGHT_GRAY)
    # Page number
    page_text = f"{slide_number + 1} / {total_slides}"
    page_font = _get_font(24)
    draw.text((width - margins, height - 55), page_text, fill=GRAY, font=page_font)

    # Footer line
    draw.rectangle([(margins, height - 30), (width - margins, height - 28)], fill=BORDER_COLOR)

    img.save(str(output_path), "PNG")
    return output_path


def render_all_slides(
    script: dict,
    output_dir: str | Path,
    width: int = SLIDE_WIDTH,
    height: int = SLIDE_HEIGHT,
) -> list[Path]:
    """Render all slides in a script to PNG files.

    Returns:
        List of Paths to the rendered PNG images
    """
    output_dir = Path(output_dir)
    slides = script.get("slides", [])
    total = len(slides)
    paths = []

    for i, slide in enumerate(slides):
        path = output_dir / f"slide_{i:03d}.png"
        render_slide(slide, path, slide_number=i, total_slides=total, width=width, height=height)
        paths.append(path)

    return paths
