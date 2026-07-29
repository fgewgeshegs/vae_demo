"""视频生成服务"""

from .script_builder import build_script
from .tts import generate_tts
from .slide_renderer import render_slide
from .composer import compose_video
from .composer import get_ffmpeg_path

__all__ = [
    "build_script",
    "generate_tts",
    "render_slide",
    "compose_video",
    "get_ffmpeg_path",
]
