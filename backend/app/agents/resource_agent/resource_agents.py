"""资源生成 Agent 群 - 6种子Agent，基于 LLM + 提示词模板 + 学习策略生成内容"""

from __future__ import annotations

import json

from loguru import logger

from app.core.llm_gateway import LLMGateway, LLMMessage
from app.prompts.resource_prompts import (
    DOCUMENT_GENERATION_PROMPT,
    MINDMAP_GENERATION_PROMPT,
    EXERCISE_GENERATION_PROMPT,
    CODE_GENERATION_PROMPT,
    READING_GENERATION_PROMPT,
    VIDEO_GENERATION_PROMPT,
)
from app.services.retriever import Retriever
from app.services.learning_strategies import LearningStrategyEngine, LearningStrategy


class BaseResourceAgent:
    """资源生成基类"""

    def __init__(self):
        self.llm = LLMGateway()
        self.retriever = Retriever()
        self.strategy_engine = LearningStrategyEngine()

    async def generate(self, params: dict) -> dict:
        """生成资源（由子类实现）"""
        raise NotImplementedError

    def _inject_strategies(self, prompt: str, params: dict) -> str:
        """注入学习策略到提示词"""
        level = params.get("level", "beginner")
        strategies = []

        # 根据水平推荐策略
        if level in ("beginner", "入门"):
            strategies = [LearningStrategy.FEYNMAN_TECHNIQUE, LearningStrategy.DUAL_CODING]
        elif level in ("intermediate", "中级"):
            strategies = [LearningStrategy.ELABORATION, LearningStrategy.INTERLEAVING]
        elif level in ("advanced", "高级"):
            strategies = [LearningStrategy.ELABORATION, LearningStrategy.ACTIVE_RECALL]

        # 构建策略上下文
        context = {}
        for s in strategies:
            context = self.strategy_engine.apply(s, context)

        # 生成策略指令并注入
        strategy_prompt = self.strategy_engine.build_strategy_prompt(strategies, context)
        if strategy_prompt:
            prompt = f"{strategy_prompt}\n\n{prompt}"

        return prompt

    async def _build_context(self, params: dict) -> str:
        """构建 RAG 上下文"""
        knowledge_point_content = params.get("knowledge_point_content") or ""
        query_parts = [
            params.get("chapter_title"),
            params.get("knowledge_point_full_title"),
            knowledge_point_content,
        ]
        query = " ".join(str(part).strip() for part in query_parts if str(part or "").strip())
        course_id = params.get("course_id")
        user_id = params.get("user_id")
        context_parts = [self._resource_scope(params)]

        def source_value(item: dict, keys: tuple[str, ...], default: str) -> str:
            for key in keys:
                value = item.get(key)
                if value:
                    return str(value)
            return default

        # 如果有知识点，检索相关教材切片
        if query:
            try:
                results = await self.retriever.retrieve(
                    query=query,
                    course_id=course_id,
                    limit=5,
                    use_vector=True,
                    user_id=user_id,
                )
                if results:
                    context_parts.append("相关教材片段：")
                    for index, r in enumerate(results, 1):
                        chapter = source_value(
                            r,
                            ("chapter_title", "chapter", "section", "locator"),
                            "章节未知",
                        )
                        document = source_value(
                            r,
                            ("document_name", "document_title", "title", "source"),
                            f"文档ID {r.get('document_id', '未知')}",
                        )
                        chunk_id = r.get("chunk_id", "未知")
                        content = str(r.get("content") or "").strip()
                        if content:
                            context_parts.append(
                                f"[片段 {index}] 文档：{document}；来源章节：{chapter}；chunk_id：{chunk_id}\n{content}"
                            )
            except Exception as e:
                logger.warning(f"RAG 检索失败: {e}")
                if str(knowledge_point_content).strip():
                    context_parts.append("RAG 检索失败，使用知识点原始内容：")
                    context_parts.append(str(knowledge_point_content).strip())

        return "\n\n".join(context_parts)

    def _resource_scope(self, params: dict) -> str:
        chapter_title = params.get("chapter_title") or ""
        knowledge_point = params.get("knowledge_point") or ""
        full_title = params.get("knowledge_point_full_title") or knowledge_point
        content = params.get("knowledge_point_content") or ""
        parts = [
            "Generate content for this exact learning-path node.",
            f"Chapter: {chapter_title or 'unknown'}",
            f"Knowledge point: {knowledge_point or full_title}",
            f"Full node title: {full_title}",
        ]
        if content:
            parts.append(f"Knowledge point content:\n{content}")
        parts.append("Do not write a generic chapter overview or reuse neighboring knowledge-point content.")
        return "\n".join(parts)

    def _scoped_prompt(self, prompt: str, params: dict) -> str:
        return f"{self._resource_scope(params)}\n\n{prompt}"

    def _display_title(self, params: dict) -> str:
        return params.get("knowledge_point_full_title") or params.get("knowledge_point") or "Learning resource"


class DocumentAgent(BaseResourceAgent):
    """课程讲义生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info(f"DocumentAgent: 开始生成讲义 - {params.get('knowledge_point', '')}")
        try:
            knowledge_point = self._display_title(params)
            level = params.get("level", "beginner")
            context = await self._build_context(params)

            prompt = DOCUMENT_GENERATION_PROMPT.format(
                knowledge_point=knowledge_point,
                level=level,
            )
            # 注入学习策略
            prompt = self._inject_strategies(prompt, params)

            if context:
                prompt = f"{context}\n\n{prompt}"

            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system_prompt="你是一个专业的课程讲师，负责生成高质量的结构化讲义。请使用中文。",
                temperature=0.7,
                max_tokens=4096,
            )

            return {
                "type": "document",
                "title": f"{knowledge_point} - 课程讲义",
                "content": response.content,
            }
        except Exception as e:
            logger.error(f"DocumentAgent 错误: {e}")
            return {"type": "document", "title": "讲义生成失败", "content": f"生成失败：{str(e)}"}


class MindMapAgent(BaseResourceAgent):
    """思维导图生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info(f"MindMapAgent: 开始生成思维导图 - {params.get('knowledge_point', '')}")
        try:
            knowledge_point = self._display_title(params)
            learning_goal = params.get("learning_goal", "掌握核心概念")

            prompt = MINDMAP_GENERATION_PROMPT.format(
                knowledge_point=knowledge_point,
                learning_goal=learning_goal,
            )
            prompt = self._scoped_prompt(prompt, params)
            # 双重编码策略对思维导图特别适用
            context = self.strategy_engine.apply(LearningStrategy.DUAL_CODING, {})
            prompt = (
                f"{context.get('prompt_instructions', '')}\n\n{prompt}"
            )

            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system_prompt="你是一个思维导图设计师。请直接返回 Mermaid 代码块。",
                temperature=0.5,
                max_tokens=2048,
            )

            return {
                "type": "mindmap",
                "title": f"{knowledge_point} - 思维导图",
                "content": response.content,
            }
        except Exception as e:
            logger.error(f"MindMapAgent 错误: {e}")
            return {"type": "mindmap", "title": "思维导图生成失败", "content": f"生成失败：{str(e)}"}


class ExerciseAgent(BaseResourceAgent):
    """练习题生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info(f"ExerciseAgent: 开始生成练习题 - {params.get('knowledge_point', '')}")
        try:
            knowledge_point = self._display_title(params)
            level = params.get("level", "beginner")

            prompt = EXERCISE_GENERATION_PROMPT.format(
                knowledge_point=knowledge_point,
                level=level,
            )
            prompt = self._scoped_prompt(prompt, params)
            # 交错练习策略对练习题特别适用
            context = self.strategy_engine.apply(LearningStrategy.INTERLEAVING, {})
            prompt = f"{context.get('prompt_instructions', '')}\n\n{prompt}"

            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system_prompt="你是一个出题专家。请生成高质量的练习题，附参考答案和解析。使用中文。",
                temperature=0.6,
                max_tokens=4096,
            )

            return {
                "type": "exercise",
                "title": f"{knowledge_point} - 练习题",
                "content": response.content,
            }
        except Exception as e:
            logger.error(f"ExerciseAgent 错误: {e}")
            return {"type": "exercise", "title": "练习题生成失败", "content": f"生成失败：{str(e)}"}


class CodeAgent(BaseResourceAgent):
    """代码案例生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info(f"CodeAgent: 开始生成代码案例 - {params.get('knowledge_point', '')}")
        try:
            knowledge_point = self._display_title(params)
            language = params.get("language", "python")

            prompt = CODE_GENERATION_PROMPT.format(
                knowledge_point=knowledge_point,
                language=language,
            )
            prompt = self._scoped_prompt(prompt, params)

            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system_prompt="你是一个编程导师。请生成完整可运行的代码示例，加中文注释。",
                temperature=0.5,
                max_tokens=4096,
            )

            return {
                "type": "code",
                "title": f"{knowledge_point} - 代码案例",
                "content": response.content,
            }
        except Exception as e:
            logger.error(f"CodeAgent 错误: {e}")
            return {"type": "code", "title": "代码生成失败", "content": f"生成失败：{str(e)}"}


class ReadingAgent(BaseResourceAgent):
    """拓展阅读生成 Agent"""

    async def generate(self, params: dict) -> dict:
        logger.info(f"ReadingAgent: 开始生成拓展阅读 - {params.get('knowledge_point', '')}")
        try:
            knowledge_point = self._display_title(params)
            level = params.get("level", "beginner")

            prompt = READING_GENERATION_PROMPT.format(
                topic=knowledge_point,
                level=level,
            )
            prompt = self._scoped_prompt(prompt, params)
            # 精细加工策略对拓展阅读特别适用
            context = self.strategy_engine.apply(LearningStrategy.ELABORATION, {})
            prompt = f"{context.get('prompt_instructions', '')}\n\n{prompt}"

            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system_prompt="你是一个学术阅读导师。推荐高质量的学习材料并说明关联。使用中文。",
                temperature=0.7,
                max_tokens=3072,
            )

            return {
                "type": "reading",
                "title": f"{knowledge_point} - 拓展阅读",
                "content": response.content,
            }
        except Exception as e:
            logger.error(f"ReadingAgent 错误: {e}")
            return {"type": "reading", "title": "拓展阅读生成失败", "content": f"生成失败：{str(e)}"}


class VideoAgent(BaseResourceAgent):
    """仿视频微课生成 Agent"""

    TEMPLATE_PHRASES = (
        "这一页围绕",
        "本镜头建立学习目标",
        "本页围绕",
        "本节将围绕",
        "通过本页学习",
    )

    def _extract_json_object(self, content: str) -> dict:
        text = (content or "").strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("video response does not contain JSON")
        data = json.loads(text[start:end + 1])
        if not isinstance(data, dict):
            raise ValueError("video response JSON must be an object")
        return data

    @staticmethod
    def _text_signature(text: str) -> set[str]:
        clean = "".join(ch.lower() for ch in str(text or "") if not ch.isspace())
        if len(clean) < 2:
            return {clean} if clean else set()
        return {clean[index : index + 2] for index in range(len(clean) - 1)}

    @classmethod
    def _text_similarity(cls, left: str, right: str) -> float:
        left_sig = cls._text_signature(left)
        right_sig = cls._text_signature(right)
        if not left_sig or not right_sig:
            return 0.0
        return len(left_sig & right_sig) / len(left_sig | right_sig)

    @classmethod
    def _validate_video_quality(cls, slides: list[dict]) -> None:
        errors = []
        slide_texts = []

        for index, slide in enumerate(slides, 1):
            title = str(slide.get("title") or "")
            bullets = [str(item) for item in slide.get("bullets", [])]
            case_detail = str(slide.get("case_detail") or "").strip()
            examples = [str(item) for item in slide.get("examples", [])]
            slide_text = "\n".join(
                [
                    title,
                    "\n".join(bullets),
                    "\n".join(str(item) for item in slide.get("key_points", [])),
                    case_detail,
                    "\n".join(examples),
                    str(slide.get("caption") or ""),
                    str(slide.get("teacher_script") or ""),
                ]
            )
            slide_texts.append((index, slide_text))

            if len(case_detail) < 60 and "教材中未提供具体案例" not in case_detail:
                errors.append(f"第 {index} 页 case_detail 太短")

            repeated_bullets = [
                bullet
                for bullet in bullets
                if title and (title in bullet or cls._text_similarity(title, bullet) >= 0.72)
            ]
            if len(repeated_bullets) >= max(2, len(bullets) // 2):
                errors.append(f"第 {index} 页 bullets 与标题高度重复")

            if any(phrase in slide_text for phrase in cls.TEMPLATE_PHRASES):
                errors.append(f"第 {index} 页出现模板句")

        for left_pos, (left_index, left_text) in enumerate(slide_texts):
            for right_index, right_text in slide_texts[left_pos + 1 :]:
                if cls._text_similarity(left_text, right_text) >= 0.82:
                    errors.append(f"第 {left_index} 页和第 {right_index} 页内容相似度过高")

        if errors:
            raise ValueError("；".join(errors[:6]))

    @staticmethod
    def _srt_timestamp(seconds: int | float) -> str:
        safe_seconds = max(0, int(seconds or 0))
        hours = safe_seconds // 3600
        minutes = (safe_seconds % 3600) // 60
        rest = safe_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{rest:02d},000"

    @classmethod
    def _build_subtitles(cls, slides: list[dict]) -> str:
        blocks = []
        for index, slide in enumerate(slides, 1):
            caption = str(slide.get("caption") or slide.get("teacher_script") or slide.get("title") or "").strip()
            if not caption:
                caption = "请结合本页要点完成理解和复述。"
            blocks.append(
                "\n".join(
                    [
                        str(index),
                        f"{cls._srt_timestamp(slide.get('start', 0))} --> {cls._srt_timestamp(slide.get('end', 0))}",
                        caption,
                    ]
                )
            )
        return "\n\n".join(blocks)

    @staticmethod
    def _build_static_page(slide: dict, index: int, title: str) -> dict:
        bullets = [str(item).strip() for item in slide.get("bullets", []) if str(item).strip()]
        keywords = []
        visual = slide.get("visual") if isinstance(slide.get("visual"), dict) else {}
        if isinstance(visual.get("keywords"), list):
            keywords = [str(item).strip() for item in visual["keywords"] if str(item).strip()]
        html_bullets = "".join(f"<li>{item}</li>" for item in bullets[:5])
        html_keywords = "".join(f"<span>{item}</span>" for item in keywords[:4])
        html = (
            '<section class="lesson-page">'
            f"<p class=\"eyebrow\">{title} · 第 {index} 页</p>"
            f"<h1>{slide.get('title') or f'第 {index} 页'}</h1>"
            f"<div class=\"visual\">{html_keywords}</div>"
            f"<ul>{html_bullets}</ul>"
            f"<p class=\"caption\">{slide.get('caption') or ''}</p>"
            "</section>"
        )
        return {
            "page_id": f"slide_{index:02d}",
            "title": str(slide.get("title") or f"第 {index} 页"),
            "duration_seconds": max(1, int(slide.get("end", 0)) - int(slide.get("start", 0))),
            "html": html,
            "visual_type": visual.get("type", "concept"),
            "keywords": keywords,
        }

    @classmethod
    def _build_video_production_pack(cls, payload: dict) -> dict:
        title = str(payload.get("title") or "个性化微课")
        slides = payload.get("slides") if isinstance(payload.get("slides"), list) else []
        script = []
        voiceover_segments = []
        static_pages = []
        timeline = []

        for index, slide in enumerate(slides, 1):
            teacher_script = str(slide.get("teacher_script") or slide.get("caption") or "").strip()
            if not teacher_script:
                teacher_script = f"请围绕“{slide.get('title') or title}”讲解本页核心内容。"
            page = cls._build_static_page(slide, index, title)
            static_pages.append(page)
            script.append(
                {
                    "scene": index,
                    "start": slide.get("start", 0),
                    "end": slide.get("end", 0),
                    "title": slide.get("title") or page["title"],
                    "screen_bullets": slide.get("bullets", []),
                    "narration": teacher_script,
                    "subtitle": slide.get("caption") or teacher_script[:90],
                    "visual_instruction": slide.get("visual") or {},
                }
            )
            voiceover_segments.append(
                {
                    "id": f"voice_{index:02d}",
                    "text": teacher_script,
                    "start": slide.get("start", 0),
                    "end": slide.get("end", 0),
                    "suggested_voice": "zh-CN-XiaoxiaoNeural",
                    "output_file": f"voice_{index:02d}.wav",
                }
            )
            timeline.append(
                {
                    "start": slide.get("start", 0),
                    "end": slide.get("end", 0),
                    "page": page["page_id"],
                    "audio": f"voice_{index:02d}.wav",
                    "subtitle": "subtitles.srt",
                }
            )

        return {
            "pipeline": "script_subtitle_voice_static_pages",
            "agents": [
                {"name": "教学脚本智能体", "output": "script"},
                {"name": "字幕智能体", "output": "subtitles_srt"},
                {"name": "语音脚本智能体", "output": "voiceover_segments"},
                {"name": "静态页面智能体", "output": "static_pages"},
                {"name": "视频合成智能体", "output": "composition_plan"},
            ],
            "script": script,
            "subtitles_srt": cls._build_subtitles(slides),
            "voiceover_segments": voiceover_segments,
            "voiceover_text": "\n\n".join(item["text"] for item in voiceover_segments),
            "static_pages": static_pages,
            "composition_plan": {
                "canvas": {"width": 1920, "height": 1080, "fps": 30},
                "timeline": timeline,
                "recommended_tools": ["Edge TTS", "Playwright screenshot", "FFmpeg"],
                "ffmpeg_outline": (
                    "先将 static_pages 渲染为 slide_XX.png，再用 TTS 生成 voice_XX.wav，"
                    "最后按 timeline 拼接图片、音频和 subtitles.srt 输出 MP4。"
                ),
            },
        }

    def _normalize_video_payload(self, payload: dict, title: str) -> dict:
        slides = payload.get("slides") if isinstance(payload, dict) else []
        clean_slides = []
        cursor = 0
        for index, raw_slide in enumerate(slides if isinstance(slides, list) else []):
            if not isinstance(raw_slide, dict):
                continue
            start = int(raw_slide.get("start", cursor) or cursor)
            end = int(raw_slide.get("end", start + 30) or start + 30)
            if end <= start:
                end = start + 30
            bullets = raw_slide.get("bullets", [])
            if not isinstance(bullets, list):
                bullets = [str(bullets)]
            bullets = [str(item).strip() for item in bullets if str(item).strip()]
            if len(bullets) < 4:
                bullets.extend([
                    "用教材事实支撑本页结论",
                    "把抽象概念转化为可观察的应用场景",
                    "通过一个问题检查是否真正理解",
                ][: 4 - len(bullets)])
            examples = raw_slide.get("examples", [])
            if not isinstance(examples, list):
                examples = [str(examples)]
            teacher_script = str(
                raw_slide.get("teacher_script")
                or raw_slide.get("speaker_notes")
                or raw_slide.get("caption")
                or ""
            ).strip()
            if not teacher_script:
                teacher_script = f"本页围绕“{raw_slide.get('title') or title}”展开讲解，先给出关键判断，再结合教材内容说明它为什么重要。"
            interaction_question = str(
                raw_slide.get("interaction_question")
                or raw_slide.get("question")
                or "你能用自己的话复述本页最重要的结论吗？"
            ).strip()
            clean_slides.append({
                "start": start,
                "end": end,
                "title": str(raw_slide.get("title") or f"第 {index + 1} 页"),
                "bullets": bullets[:6],
                "core_question": str(raw_slide.get("core_question") or "").strip(),
                "key_points": [
                    str(item).strip()
                    for item in (raw_slide.get("key_points") if isinstance(raw_slide.get("key_points"), list) else [])
                    if str(item).strip()
                ][:4],
                "case_detail": str(raw_slide.get("case_detail") or "").strip(),
                "misconception": str(raw_slide.get("misconception") or "").strip(),
                "self_check": str(raw_slide.get("self_check") or "").strip(),
                "caption": str(raw_slide.get("caption") or teacher_script[:90]),
                "teacher_script": teacher_script,
                "examples": [str(item).strip() for item in examples if str(item).strip()][:3],
                "interaction_question": interaction_question,
                "visual": raw_slide.get("visual") if isinstance(raw_slide.get("visual"), dict) else {},
            })
            cursor = end

        if not clean_slides:
            clean_slides = self._fallback_video_slides(title)
        else:
            self._validate_video_quality(clean_slides)

        duration = max((slide["end"] for slide in clean_slides), default=180)
        normalized = {
            "mode": "video_like_slides",
            "title": str(payload.get("title") or title),
            "duration_seconds": int(payload.get("duration_seconds") or duration),
            "slides": clean_slides,
        }
        normalized["production_pack"] = self._build_video_production_pack(normalized)
        return normalized

    def _fallback_video_slides(self, title: str) -> list[dict]:
        topics = [
            ("学习目标", "先明确本节要解决的问题，再建立后续学习的观察线索。", "concept"),
            ("核心概念拆解", "把概念拆成定义、作用、条件和结果四个层次来理解。", "concept"),
            ("教材案例讲解", "结合教材中的事实或案例说明概念如何落地。", "flow"),
            ("关键对比", "比较相近概念或不同方案，找到最容易混淆的边界。", "compare"),
            ("应用迁移", "把本节知识迁移到新的问题场景，形成可复用的方法。", "flow"),
            ("总结自测", "用一个小问题检查是否能独立复述和应用。", "quiz"),
        ]
        slides = []
        cursor = 0
        for index, (slide_title, script, visual_type) in enumerate(topics):
            end = cursor + 32
            bullets = [
                f"{title}：{slide_title}",
                script,
                "保留一个关键词作为后续复习线索",
                "尝试用自己的话解释给同伴听",
            ]
            slides.append({
                "start": cursor,
                "end": end,
                "title": slide_title,
                "bullets": bullets,
                "core_question": f"学习“{slide_title}”时，最需要先回答什么问题？",
                "key_points": bullets[:3],
                "case_detail": script,
                "misconception": "不要只记住标题，要结合背景、过程、结果和应用场景来理解。",
                "self_check": f"请用自己的话解释“{slide_title}”和“{title}”之间的关系。",
                "caption": script,
                "teacher_script": f"这一页围绕“{slide_title}”展开。{script}学习时不要只记住标题，要能说出它和前后知识点的关系。",
                "examples": [f"围绕“{title}”构造一个课堂例子", "把教材中的一句原文转化成自己的解释"],
                "interaction_question": "如果让你向同学解释这一页，你会先说哪一句？",
                "visual": {"type": visual_type, "keywords": [title, slide_title, "解释", "应用"]},
            })
            cursor = end
        return slides

    async def generate(self, params: dict) -> dict:
        logger.info(f"VideoAgent: 开始生成仿视频微课 - {params.get('knowledge_point', '')}")
        try:
            knowledge_point = self._display_title(params)
            script_format = params.get("format", "video_like_slides JSON")
            rag_context = await self._build_context(params)

            prompt = VIDEO_GENERATION_PROMPT.format(
                knowledge_point=knowledge_point,
                format=script_format,
            )
            if rag_context:
                prompt = f"{rag_context}\n\n{prompt}"
            else:
                prompt = self._scoped_prompt(prompt, params)
            prompt = (
                f"{prompt}\n\n"
                "自主学习型幻灯片内容要求：每一页 slide 除 bullets 外，必须额外包含以下字段："
                "core_question、key_points、case_detail、misconception、self_check。"
                "所有 key_points、case_detail、examples 必须来自上方“相关教材片段”或知识点原始内容，"
                "不允许只根据标题、章节名或常识自行生成。"
                "如果检索上下文没有提供具体案例，case_detail 或 examples 中必须明确写“教材中未提供具体案例”，"
                "不要编造案例、场景、数据、风险、机制或固定话术。"
                "每一页必须至少包含一个教材事实、一个基于该事实的解释、一个可自测问题；"
                "教材事实必须能在检索到的教材内容中找到依据。"
                "core_question 要写成学习者需要回答的具体问题；key_points 必须是 3-4 条可学习的解释，不允许只重复标题；"
                "case_detail 必须结合教材内容、案例事实或真实应用场景展开，至少 60 个中文字符；"
                "misconception 要指出常见误解或易错边界；self_check 要给出可自测的问题。"
                "如果知识点是“教材案例”，必须明确写出案例背景、风险或机制、结论或启示。"
                "禁止输出空泛句式，例如“这一页围绕某某展开”“本镜头建立学习目标”。"
            )
            prompt = (
                f"{prompt}\n\n"
                "请不要生成真实视频文件，也不要输出普通脚本。请生成一个仿视频微课播放器可用的严格 JSON 对象：\n"
                "{\n"
                '  "mode": "video_like_slides",\n'
                '  "title": "微课标题",\n'
                '  "duration_seconds": 180,\n'
                '  "slides": [\n'
                "    {\n"
                '      "start": 0,\n'
                '      "end": 30,\n'
                '      "title": "本页标题",\n'
                '      "bullets": ["屏幕要点1：包含具体事实", "屏幕要点2：解释原因或过程", "屏幕要点3：给出例子", "屏幕要点4：提示易错点"],\n'
                '      "caption": "屏幕底部显示的字幕式讲解文案，60-100字",\n'
                '      "teacher_script": "教师讲解稿，120-180字，要像课堂讲解，不要只写标题。",\n'
                '      "examples": ["教材或现实例子1", "迁移应用例子2"],\n'
                '      "interaction_question": "本页结束时抛给学习者的思考问题",\n'
                '      "visual": {"type": "concept", "keywords": ["关键词1", "关键词2", "关键词3", "关键词4"]}\n'
                "    }\n"
                "  ]\n"
                "}\n"
                "要求：6-8 页，start/end 连续递增，总时长 3-5 分钟；每页 bullets 至少 4 条，必须包含事实、解释、例子和易错点；"
                "caption 60-100 字，teacher_script 120-180 字；examples 至少 2 条；visual.keywords 至少 4 个。"
                "visual.type 可用 concept、timeline、flow、compare、quote、quiz。"
                "只输出 JSON，不要输出 Markdown。"
            )
            # 双重编码策略对视频脚本特别适用
            context = self.strategy_engine.apply(LearningStrategy.DUAL_CODING, {})
            prompt = f"{context.get('prompt_instructions', '')}\n\n{prompt}"
            system_prompt = (
                "你是一个仿视频微课 JSON 数据生成器。"
                "只能输出可被 JSON.parse 解析的 JSON 对象；"
                "不要输出 Markdown、代码块、场景脚本、旁白段落或解释文字。"
                "使用中文内容。"
            )

            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=4096,
            )
            try:
                payload = self._normalize_video_payload(
                    self._extract_json_object(response.content),
                    f"{knowledge_point} - 仿视频微课",
                )
            except ValueError as quality_error:
                logger.warning(f"VideoAgent 内容质量校验失败，尝试重新生成: {quality_error}")
                repair_prompt = (
                    f"{prompt}\n\n"
                    f"上一次输出未通过内容质量校验：{quality_error}\n"
                    "请重新生成完整 JSON。必须修复这些问题：case_detail 不得过短；"
                    "bullets 不能重复标题；各页内容不能高度相似；"
                    "禁止出现“这一页围绕…”“本镜头建立学习目标”等模板句。"
                    "如果教材上下文没有具体案例，写“教材中未提供具体案例”。"
                )
                response = await self.llm.chat(
                    messages=[LLMMessage("user", repair_prompt)],
                    system_prompt=system_prompt,
                    temperature=0.6,
                    max_tokens=4096,
                )
                payload = self._normalize_video_payload(
                    self._extract_json_object(response.content),
                    f"{knowledge_point} - 仿视频微课",
                )

            return {
                "type": "video",
                "title": f"{knowledge_point} - 仿视频微课",
                "content": json.dumps(payload, ensure_ascii=False, indent=2),
            }
        except Exception as e:
            logger.error(f"VideoAgent 错误: {e}")
            title = self._display_title(params)
            payload = self._normalize_video_payload({}, f"{title} - 仿视频微课")
            return {
                "type": "video",
                "title": f"{title} - 仿视频微课",
                "content": json.dumps(payload, ensure_ascii=False, indent=2),
            }
