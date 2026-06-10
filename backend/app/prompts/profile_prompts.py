"""画像 Agent 提示词模板"""

PROFILE_EXTRACTION_PROMPT = """你是学习者画像分析专家。从用户对话中提取学习特征，更新 JSON 画像。
当前画像：
{current_profile}

用户消息：{message}

请分析并输出增量更新（只修改有证据支持的字段），JSON 格式：
{{
    "knowledge_base": {{"level": "beginner|intermediate|advanced", "subjects": [...]}},
    "cognitive_style": {{"preference": "visual|auditory|reading|kinesthetic", "description": "..."}},
    "learning_goals": {{"short_term": "...", "long_term": "..."}},
    "knowledge_gaps": ["gap1", "gap2"],
    "learning_pace": {{"speed": "slow|normal|fast", "preferred_session_minutes": 30}},
    "interest_direction": {{"areas": ["area1", "area2"]}},
    "weak_points": ["point1", "point2"]
}}

只返回 JSON，不要额外说明。"""


PROFILE_UPDATE_PROMPT = """请根据之前的画像和新对话进行加权更新。
旧维度权重衰减系数 0.9，新信息权重 0.1。
当前画像：{current_profile}
新对话：{message}
"""
