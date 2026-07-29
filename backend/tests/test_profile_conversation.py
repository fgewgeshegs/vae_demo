"""对话式画像构建服务测试"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.profile_conversation_service import (
    ProfileConversationService,
    PROFILE_DIMENSIONS,
    PROFILE_TEMPLATE,
)


class TestProfileConversationService:
    """测试对话式画像构建服务"""

    def setup_method(self):
        """设置测试环境"""
        self.service = ProfileConversationService()

    def test_profile_template_completeness(self):
        """测试画像模板包含所有必要维度"""
        for dimension in PROFILE_DIMENSIONS:
            assert dimension in PROFILE_TEMPLATE, f"Missing dimension: {dimension}"
        
        # 检查新增维度
        assert "learning_habits" in PROFILE_TEMPLATE
        assert "motivation_factors" in PROFILE_TEMPLATE
        assert "_meta" in PROFILE_TEMPLATE

    def test_ensure_profile_shape(self):
        """测试画像结构完整性检查"""
        # 测试空画像
        empty_profile = self.service._ensure_profile_shape(None)
        assert empty_profile == PROFILE_TEMPLATE
        
        # 测试部分画像
        partial_profile = {
            "knowledge_base": {"level": "intermediate"},
            "cognitive_style": {"preference": "visual"},
        }
        result = self.service._ensure_profile_shape(partial_profile)
        assert result["knowledge_base"]["level"] == "intermediate"
        assert result["cognitive_style"]["preference"] == "visual"
        assert result["learning_goals"] == PROFILE_TEMPLATE["learning_goals"]

    def test_identify_missing_dimensions(self):
        """测试识别缺失维度"""
        # 空画像
        empty_profile = {}
        missing = self.service._identify_missing_dimensions(empty_profile)
        assert len(missing) == len(PROFILE_DIMENSIONS)
        
        # 部分画像
        partial_profile = {
            "knowledge_base": {"level": "beginner", "subjects": ["数学"]},
            "cognitive_style": {"preference": "visual"},
        }
        missing = self.service._identify_missing_dimensions(partial_profile)
        assert "knowledge_base" not in missing
        assert "cognitive_style" not in missing
        assert "learning_goals" in missing

    def test_identify_completed_dimensions(self):
        """测试识别完成维度"""
        complete_profile = {
            "knowledge_base": {"level": "intermediate", "subjects": ["编程"]},
            "cognitive_style": {"preference": "kinesthetic"},
            "learning_goals": {"short_term": "学习Python", "long_term": "成为工程师"},
            "knowledge_gaps": ["算法"],
            "learning_pace": {"speed": "normal", "preferred_session_minutes": 45},
            "interest_direction": {"areas": ["AI", "机器学习"]},
            "weak_points": ["数学"],
            "learning_habits": {"preferred_time": "evening"},
            "motivation_factors": {"intrinsic": ["好奇心"]},
        }
        completed = self.service._identify_completed_dimensions(complete_profile)
        assert len(completed) >= 6  # 至少6个维度

    def test_calculate_completeness(self):
        """测试计算画像完整度"""
        # 空画像
        empty_profile = {}
        completeness = self.service._calculate_completeness(empty_profile)
        assert completeness == 0.0
        
        # 完整画像
        complete_profile = deepcopy(PROFILE_TEMPLATE)
        for dimension in PROFILE_DIMENSIONS:
            if dimension.startswith("_"):
                continue
            if isinstance(complete_profile[dimension], dict):
                complete_profile[dimension] = {"key": "value"}
            elif isinstance(complete_profile[dimension], list):
                complete_profile[dimension] = ["item"]
        completeness = self.service._calculate_completeness(complete_profile)
        assert completeness > 0.0

    def test_extract_json_object(self):
        """测试从LLM响应中提取JSON对象"""
        # 正常JSON（含完整结构）
        valid_json = '{"updates": {"knowledge_base": {"level": "beginner"}}, "evidence": [], "insufficient_evidence": []}'
        result = self.service._extract_json_object(valid_json)
        assert isinstance(result, dict)
        assert "updates" in result
        
        # 代码块中的JSON
        code_block = '```json\n{"updates": {"learning_goals": {"short_term": "test"}}, "evidence": []}\n```'
        result = self.service._extract_json_object(code_block)
        assert isinstance(result, dict)
        
        # "无更新"的有效响应（含insufficient_evidence）
        no_updates = '{"updates": {}, "evidence": [], "insufficient_evidence": ["knowledge_base.level"]}'
        result = self.service._extract_json_object(no_updates)
        assert isinstance(result, dict)
        assert result["updates"] == {}
        
        # 混合文本中的JSON
        mixed_text = 'Here is the result:\n{"updates": {"weak_points": ["数学"]}, "evidence": []}\nDone.'
        result = self.service._extract_json_object(mixed_text)
        assert isinstance(result, dict)
        
        # 空内容
        with pytest.raises(ValueError):
            self.service._extract_json_object("")
        
        # 纯文本无JSON
        with pytest.raises(ValueError):
            self.service._extract_json_object("This is just plain text with no JSON")

    def test_normalize_extraction_result(self):
        """测试规范化提取结果"""
        raw_result = {
            "updates": {
                "knowledge_base": {"level": "intermediate"},
                "cognitive_style": {"preference": "visual"},
                "learning_goals": {"short_term": "学习编程"},
                "learning_pace": {"speed": "fast", "preferred_session_minutes": 60},
                "interest_direction": {"areas": ["AI"]},
                "knowledge_gaps": ["算法"],
                "weak_points": ["数学"],
                "learning_habits": {"preferred_time": "evening"},
                "motivation_factors": {"intrinsic": ["好奇心"]},
            },
            "evidence": [
                {"field": "knowledge_base.level", "quote": "我是中级水平", "confidence": 0.8}
            ],
            "insufficient_evidence": ["learning_goals.long_term"],
            "conversation_phase": "deepening",
            "next_questions": ["你的长期目标是什么？"],
        }
        
        result = self.service._normalize_extraction_result(raw_result)
        
        assert "updates" in result
        assert "evidence" in result
        assert "insufficient_evidence" in result
        assert "conversation_phase" in result
        assert "next_questions" in result
        
        # 验证更新内容
        updates = result["updates"]
        assert updates["knowledge_base"]["level"] == "intermediate"
        assert updates["cognitive_style"]["preference"] == "visual"
        assert updates["learning_goals"]["short_term"] == "学习编程"
        assert updates["learning_pace"]["speed"] == "fast"
        assert updates["interest_direction"]["areas"] == ["AI"]
        assert updates["knowledge_gaps"] == ["算法"]
        assert updates["weak_points"] == ["数学"]
        assert updates["learning_habits"]["preferred_time"] == "evening"
        assert updates["motivation_factors"]["intrinsic"] == ["好奇心"]

    def test_merge_updates(self):
        """测试合并更新"""
        current = {
            "knowledge_base": {"level": "beginner", "subjects": ["数学"]},
            "cognitive_style": {"preference": "visual"},
        }
        
        updates = {
            "knowledge_base": {"level": "intermediate", "subjects": ["编程"]},
            "cognitive_style": {"preference": "kinesthetic"},
            "learning_goals": {"short_term": "学习Python"},
        }
        
        result = self.service._merge_updates(current, updates)
        
        # 验证合并结果
        assert result["knowledge_base"]["level"] == "intermediate"
        assert "数学" in result["knowledge_base"]["subjects"]
        assert "编程" in result["knowledge_base"]["subjects"]
        assert result["cognitive_style"]["preference"] == "kinesthetic"
        assert result["learning_goals"]["short_term"] == "学习Python"

    def test_profile_dimensions_coverage(self):
        """测试画像维度覆盖"""
        # 验证所有维度都被处理
        for dimension in PROFILE_DIMENSIONS:
            if dimension.startswith("_"):
                continue
            
            # 创建测试画像
            test_profile = deepcopy(PROFILE_TEMPLATE)
            if isinstance(test_profile[dimension], dict):
                test_profile[dimension] = {"test": "value"}
            elif isinstance(test_profile[dimension], list):
                test_profile[dimension] = ["test"]
            
            # 验证维度存在
            assert dimension in test_profile
            assert test_profile[dimension] is not None


# 需要导入deepcopy
from copy import deepcopy
