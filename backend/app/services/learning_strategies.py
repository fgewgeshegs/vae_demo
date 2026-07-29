"""学习策略引擎 - 贯穿所有 Agent

提供 6 大学习策略的上下文注入和应用：
1. 间隔重复（Spaced Repetition）
2. 费曼学习法（Feynman Technique）
3. 主动回忆（Active Recall）
4. 交错练习（Interleaving）
5. 双重编码（Dual Coding）
6. 精细加工（Elaboration）
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional


class LearningStrategy(str, Enum):
    SPACED_REPETITION = "spaced_repetition"       # 间隔重复
    FEYNMAN_TECHNIQUE = "feynman_technique"        # 费曼学习法
    ACTIVE_RECALL = "active_recall"                # 主动回忆
    INTERLEAVING = "interleaving"                  # 交错练习
    DUAL_CODING = "dual_coding"                    # 双重编码
    ELABORATION = "elaboration"                    # 精细加工


class LearningStrategyEngine:
    """学习策略引擎 - 根据用户画像和学习数据推荐并应用策略"""

    def __init__(self):
        self.strategies = {
            LearningStrategy.SPACED_REPETITION: self._apply_spaced_repetition,
            LearningStrategy.FEYNMAN_TECHNIQUE: self._apply_feynman,
            LearningStrategy.ACTIVE_RECALL: self._apply_active_recall,
            LearningStrategy.INTERLEAVING: self._apply_interleaving,
            LearningStrategy.DUAL_CODING: self._apply_dual_coding,
            LearningStrategy.ELABORATION: self._apply_elaboration,
        }

    def apply(self, strategy: LearningStrategy, context: Dict[str, Any]) -> Dict[str, Any]:
        """应用特定学习策略，返回增强后的上下文"""
        handler = self.strategies.get(strategy)
        if handler:
            return handler(context)
        return context

    def recommend_strategies(self, profile: Optional[Dict[str, Any]] = None) -> List[LearningStrategy]:
        """根据用户画像推荐最适合的学习策略"""
        if not profile:
            return [LearningStrategy.SPACED_REPETITION, LearningStrategy.FEYNMAN_TECHNIQUE]

        cognitive_style = profile.get("cognitive_style", {})
        preference = cognitive_style.get("preference", "")
        level = profile.get("knowledge_base", {}).get("level", "beginner")
        gaps = profile.get("knowledge_gaps", [])

        recommended = []

        # 默认策略
        recommended.append(LearningStrategy.SPACED_REPETITION)

        # 根据认知风格推荐
        if "视觉" in preference or "visual" in preference.lower():
            recommended.append(LearningStrategy.DUAL_CODING)
        if "逻辑" in preference or "logical" in preference.lower():
            recommended.append(LearningStrategy.ELABORATION)
        if "实践" in preference or "practical" in preference.lower():
            recommended.append(LearningStrategy.ACTIVE_RECALL)

        # 根据水平推荐
        if level in ("beginner", "入门"):
            recommended.append(LearningStrategy.FEYNMAN_TECHNIQUE)
        elif level in ("intermediate", "中级"):
            recommended.extend([LearningStrategy.INTERLEAVING, LearningStrategy.ACTIVE_RECALL])
        elif level in ("advanced", "高级"):
            recommended.extend([LearningStrategy.ELABORATION, LearningStrategy.INTERLEAVING])

        # 如果有知识短板，加入主动回忆策略
        if gaps and len(gaps) > 0:
            if LearningStrategy.ACTIVE_RECALL not in recommended:
                recommended.append(LearningStrategy.ACTIVE_RECALL)

        return recommended[:4]  # 最多推荐 4 个

    def build_strategy_prompt(self, strategies: List[LearningStrategy], context: Dict[str, Any]) -> str:
        """构建策略提示词，注入到 Agent 的 prompt 中"""
        if not strategies:
            return ""

        strategy_descriptions = {
            LearningStrategy.SPACED_REPETITION: (
                "- 间隔重复策略：在关键时间点安排复习（1天、3天、7天、14天、30天后），"
                "帮助巩固长期记忆"
            ),
            LearningStrategy.FEYNMAN_TECHNIQUE: (
                "- 费曼学习法策略：用最简单的语言解释概念，类比生活中的例子，"
                "检查是否存在理解盲区"
            ),
            LearningStrategy.ACTIVE_RECALL: (
                "- 主动回忆策略：在复习前先尝试回忆知识点，而不是直接阅读材料；"
                "通过自我测试来强化记忆"
            ),
            LearningStrategy.INTERLEAVING: (
                "- 交错练习策略：混合不同主题的练习题，交替练习不同类型的问题，"
                "提高知识迁移能力"
            ),
            LearningStrategy.DUAL_CODING: (
                "- 双重编码策略：同时使用文字和视觉方式呈现信息，"
                "包含图示、图表、思维导图等可视化元素"
            ),
            LearningStrategy.ELABORATION: (
                "- 精细加工策略：将新知识与已有知识建立联系，"
                '追问"为什么"，提供具体示例和实际应用场景'
            ),
        }

        parts = ["【学习策略】请在教学过程中应用以下学习策略："]
        for s in strategies:
            desc = strategy_descriptions.get(s, "")
            if desc:
                parts.append(desc)

        return "\n".join(parts)

    def _apply_spaced_repetition(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """间隔重复策略"""
        context["strategy_name"] = "间隔重复"
        context["strategy_description"] = "在关键时间点安排复习"
        context["review_intervals"] = [1, 3, 7, 14, 30]  # 天
        context["review_schedule"] = "new_today_review_tomorrow"
        context["prompt_instructions"] = (
            "请按照[1天后、3天后、7天后、14天后、30天后]的时间间隔安排复习计划，"
            "在每个复习节点标注复习内容和重点。"
        )
        return context

    def _apply_feynman(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """费曼学习法策略"""
        context["strategy_name"] = "费曼学习法"
        context["strategy_description"] = "用最简单的语言解释概念"
        context["teaching_approach"] = "explain_in_simple_terms"
        context["check_understanding"] = True
        context["prompt_instructions"] = (
            "请用最简单的语言和生活中的类比来解释概念，确保一个初学者也能理解。"
            "在解释后，提出引导性问题来检查理解程度。"
            "如果用户表现出困惑，尝试从另一个角度重新解释。"
        )
        return context

    def _apply_active_recall(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """主动回忆策略"""
        context["strategy_name"] = "主动回忆"
        context["strategy_description"] = "在复习前先尝试回忆"
        context["recall_prompts"] = True
        context["test_before_review"] = True
        context["prompt_instructions"] = (
            "在呈现新内容前，先提出问题让学习者尝试回忆已学知识。"
            "设计自我测试环节，让学习者在查看答案前先尝试回答。"
            "间隔性地检查学习者的记忆保持情况。"
        )
        return context

    def _apply_interleaving(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """交错练习策略"""
        context["strategy_name"] = "交错练习"
        context["strategy_description"] = "混合不同主题练习"
        context["mix_topics"] = True
        context["alternate_problem_types"] = True
        context["prompt_instructions"] = (
            "在练习环节混合不同主题的问题，交替出现不同类型（选择、填空、简答）的题目。"
            "避免连续出现同一类型或同一主题的题目。"
            "设计需要综合运用多个知识点才能解决的问题。"
        )
        return context

    def _apply_dual_coding(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """双重编码策略"""
        context["strategy_name"] = "双重编码"
        context["strategy_description"] = "图文并茂呈现信息"
        context["visual_diagrams"] = True
        context["text_and_image"] = True
        context["prompt_instructions"] = (
            "在文字解释的同时，使用 Mermaid 语法生成图示（流程图、思维导图、结构图等）。"
            "用视觉化的方式呈现知识结构，将抽象概念转化为直观图像。"
            "在关键概念处配以示意图或关系图。"
        )
        return context

    def _apply_elaboration(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """精细加工策略"""
        context["strategy_name"] = "精细加工"
        context["strategy_description"] = "建立知识之间的联系"
        context["examples_and_connections"] = True
        context["why_questions"] = True
        context["prompt_instructions"] = (
            "将新知识与学习者已有的知识建立联系，引用之前学过的概念。"
            "提供丰富的实际应用场景和具体案例。"
            '多问"为什么"，引导学习者思考原理和因果关系。'
            "鼓励学习者用自己的话复述知识点。"
        )
        return context

    def apply_chapter_strategies(self, chapter_info: dict, profile: dict) -> Dict[str, Any]:
        """为整个章节应用学习策略"""
        context = {}
        
        # 根据章节特点推荐策略
        chapter_strategies = self.get_chapter_strategy_recommendations(chapter_info, profile)
        
        # 应用每个策略
        for strategy in chapter_strategies:
            context = self.apply(strategy, context)
        
        # 添加章节特定的上下文
        context["chapter_title"] = chapter_info.get("title", "")
        context["knowledge_point_count"] = len(chapter_info.get("knowledge_points", []))
        context["total_estimated_minutes"] = chapter_info.get("total_estimated_minutes", 0)
        
        return context
    
    def get_chapter_strategy_recommendations(self, chapter_info: dict, profile: dict) -> List[LearningStrategy]:
        """根据章节特点推荐学习策略"""
        recommendations = []
        
        # 基础策略：间隔重复
        recommendations.append(LearningStrategy.SPACED_REPETITION)
        
        # 根据章节内容特点推荐策略
        knowledge_points = chapter_info.get("knowledge_points", [])
        has_complex_concepts = any(
            kp.get("difficulty") in ("hard", "困难") 
            for kp in knowledge_points
        )
        has_practical_content = any(
            "实践" in kp.get("title", "") or "案例" in kp.get("title", "")
            for kp in knowledge_points
        )
        
        # 复杂概念：推荐费曼学习法和主动回忆
        if has_complex_concepts:
            if LearningStrategy.FEYNMAN_TECHNIQUE not in recommendations:
                recommendations.append(LearningStrategy.FEYNMAN_TECHNIQUE)
            if LearningStrategy.ACTIVE_RECALL not in recommendations:
                recommendations.append(LearningStrategy.ACTIVE_RECALL)
        
        # 实践内容：推荐交错练习
        if has_practical_content:
            if LearningStrategy.INTERLEAVING not in recommendations:
                recommendations.append(LearningStrategy.INTERLEAVING)
        
        # 根据学生画像推荐策略
        cognitive_style = profile.get("cognitive_style", {})
        preference = cognitive_style.get("preference", "").lower()
        
        if "视觉" in preference or "visual" in preference:
            if LearningStrategy.DUAL_CODING not in recommendations:
                recommendations.append(LearningStrategy.DUAL_CODING)
        
        if "逻辑" in preference or "logical" in preference:
            if LearningStrategy.ELABORATION not in recommendations:
                recommendations.append(LearningStrategy.ELABORATION)
        
        # 根据学生水平推荐策略
        level = profile.get("knowledge_base", {}).get("level", "beginner")
        if level in ("beginner", "入门"):
            if LearningStrategy.FEYNMAN_TECHNIQUE not in recommendations:
                recommendations.append(LearningStrategy.FEYNMAN_TECHNIQUE)
        elif level in ("advanced", "高级"):
            if LearningStrategy.ELABORATION not in recommendations:
                recommendations.append(LearningStrategy.ELABORATION)
            if LearningStrategy.INTERLEAVING not in recommendations:
                recommendations.append(LearningStrategy.INTERLEAVING)
        
        # 最多推荐4个策略
        return recommendations[:4]
    
    def build_chapter_strategy_prompt(self, strategies: List[LearningStrategy], context: Dict[str, Any]) -> str:
        """为章节构建策略提示词"""
        if not strategies:
            return ""
        
        chapter_title = context.get("chapter_title", "")
        knowledge_point_count = context.get("knowledge_point_count", 0)
        
        parts = [f"【章节学习策略】针对章节《{chapter_title}》（包含 {knowledge_point_count} 个知识点），请应用以下学习策略："]
        
        # 添加策略描述
        for strategy in strategies:
            strategy_info = self.apply(strategy, {})
            strategy_name = strategy_info.get("strategy_name", "")
            strategy_description = strategy_info.get("strategy_description", "")
            prompt_instructions = strategy_info.get("prompt_instructions", "")
            
            if strategy_name:
                parts.append(f"- {strategy_name}：{strategy_description}")
                if prompt_instructions:
                    parts.append(f"  具体要求：{prompt_instructions}")
        
        # 添加章节特定的策略应用建议
        if knowledge_point_count > 5:
            parts.append("- 章节内容较多，建议将知识点分组学习，每组学习后安排复习")
        
        if context.get("total_estimated_minutes", 0) > 120:
            parts.append("- 章节学习时间较长，建议适当安排休息和复习节点")
        
        return "\n".join(parts)
    
    def get_learning_phase_strategies(self, phase: str, profile: dict) -> List[LearningStrategy]:
        """根据学习阶段推荐策略"""
        phase_strategies = {
            "preview": [LearningStrategy.DUAL_CODING],  # 预览阶段：双重编码
            "learn": [LearningStrategy.FEYNMAN_TECHNIQUE, LearningStrategy.ELABORATION],  # 学习阶段：费曼学习法+精细加工
            "practice": [LearningStrategy.INTERLEAVING, LearningStrategy.ACTIVE_RECALL],  # 练习阶段：交错练习+主动回忆
            "review": [LearningStrategy.SPACED_REPETITION, LearningStrategy.ACTIVE_RECALL],  # 复习阶段：间隔重复+主动回忆
            "exam": [LearningStrategy.ACTIVE_RECALL],  # 测试阶段：主动回忆
        }
        
        base_strategies = phase_strategies.get(phase, [])
        
        # 根据学生画像调整
        cognitive_style = profile.get("cognitive_style", {})
        preference = cognitive_style.get("preference", "").lower()
        
        adjusted_strategies = list(base_strategies)
        
        # 视觉学习者：在所有阶段增加双重编码
        if "视觉" in preference or "visual" in preference:
            if LearningStrategy.DUAL_CODING not in adjusted_strategies:
                adjusted_strategies.append(LearningStrategy.DUAL_CODING)
        
        # 实践学习者：在练习阶段增加交错练习
        if "实践" in preference or "practical" in preference:
            if phase == "practice" and LearningStrategy.INTERLEAVING not in adjusted_strategies:
                adjusted_strategies.append(LearningStrategy.INTERLEAVING)
        
        return adjusted_strategies[:3]  # 最多3个策略
