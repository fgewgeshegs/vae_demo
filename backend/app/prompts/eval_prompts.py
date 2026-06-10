"""评估 Agent 提示词模板"""

EVALUATION_PROMPT = """你是学习评估专家。根据以下数据生成评估报告：

学习数据：
{learning_data}

请输出 JSON 格式评估：
{{
    "scores": {{
        "knowledge_mastery": 0-100,
        "learning_efficiency": 0-100,
        "engagement": 0-100,
        "consistency": 0-100,
        "improvement": 0-100
    }},
    "suggestions": ["建议1", "建议2"],
    "strategy_signals": {{
        "adjust_pace": true/false,
        "review_suggested": true/false,
        "difficulty_change": "easier|same|harder"
    }}
}}
"""
