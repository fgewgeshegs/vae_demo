"""资源生成 Agent 提示词模板"""

DOCUMENT_GENERATION_PROMPT = """你是一个专业的课程讲师。请根据以下要求生成结构化 Markdown 讲义：

知识点：{knowledge_point}
学习者水平：{level}

要求：
1. 包含：概念解释、原理说明、实际应用
2. 使用标题层级组织内容
3. 加入思考题"""


MINDMAP_GENERATION_PROMPT = """你是一个思维导图设计师。请根据以下知识点生成 Mermaid 语法的思维导图：
知识点：{knowledge_point}
学习目标：{learning_goal}

要求：
1. 使用 Mermaid mindmap 语法
2. 包含主题、子主题和关键概念
3. 层级清晰，便于记忆
4. 只返回 Mermaid 代码块"""

EXERCISE_GENERATION_PROMPT = """你是一个出题专家。请根据以下知识点生成练习题：
知识点：{knowledge_point}
学习者水平：{level}

要求：
1. 包含：选择题、填空题、简答题
2. 难度递进（从易到难）
3. 附参考答案和解析
4. 数量：5-10题"""

CODE_GENERATION_PROMPT = """你是一个编程导师。请根据以下知识点生成代码示例：
知识点：{knowledge_point}
编程语言：{language}

要求：
1. 包含完整可运行的代码
2. 添加中文注释说明关键步骤
3. 包含输入输出示例
4. 代码风格规范整洁"""

READING_GENERATION_PROMPT = """你是一个学术阅读导师。请根据以下主题生成拓展阅读材料：
主题：{topic}
当前水平：{level}

要求：
1. 推荐相关的论文/文章/书籍
2. 提供每篇材料的核心观点摘要
3. 说明与当前学习内容的关联
4. 标注阅读优先级和预计阅读时间"""

VIDEO_GENERATION_PROMPT = """请根据以下知识点生成仿视频微课播放器可用的微课分镜数据：
知识点：{knowledge_point}
输出格式：{format}

要求：
1. 只输出严格 JSON 对象，不要输出 Markdown、代码块或普通脚本文字
2. JSON 必须包含 mode、title、duration_seconds、slides
3. mode 固定为 video_like_slides
4. slides 为 6-8 页，每页包含 start、end、title、bullets、caption、teacher_script、examples、interaction_question、visual
5. bullets 是屏幕要点，每页至少 4 条，必须包含具体事实、解释、例子、易错点或小结
6. caption 是字幕式讲解文案，60-100 字，不要只写一句标题
7. teacher_script 是教师讲解稿，120-180 字，要像课堂讲解
8. examples 至少 2 条，优先使用教材案例或贴近学生的应用场景
9. visual.type 可用 concept、timeline、flow、compare、quote、quiz，visual.keywords 至少 4 个且必须清晰可读
10. 时长控制在 3-5 分钟，start/end 连续递增"""
