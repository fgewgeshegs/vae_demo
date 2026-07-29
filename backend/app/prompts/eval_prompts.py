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

注意：
- score_trend_summary 仅用于判断 improvement，不要直接复制历史综合分或历史维度分。
- knowledge_mastery、learning_efficiency、engagement、consistency 必须基于本次学习数据重新判断。
- 只输出 JSON，不要输出解释文字。
"""
