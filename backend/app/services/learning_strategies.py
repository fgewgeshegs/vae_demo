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
