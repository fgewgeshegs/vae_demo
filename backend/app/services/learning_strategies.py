"""学习策略引擎 - 贯穿所有 Agent"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Any


class LearningStrategy(str, Enum):
    SPACED_REPETITION = "spaced_repetition"       # 间隔重复
    FEYNMAN_TECHNIQUE = "feynman_technique"        # 费曼学习法
    ACTIVE_RECALL = "active_recall"                # 主动回忆
    INTERLEAVING = "interleaving"                  # 交错练习
    DUAL_CODING = "dual_coding"                    # 双重编码
    ELABORATION = "elaboration"                    # 精细加工


class LearningStrategyEngine:
    """学习策略引擎"""

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
        """应用特定学习策略"""
        handler = self.strategies.get(strategy)
        if handler:
            return handler(context)
        return context

    def _apply_spaced_repetition(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """间隔重复策略"""
        context["review_intervals"] = [1, 3, 7, 14, 30]  # 天
        return context

    def _apply_feynman(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """费曼学习法策略"""
        context["teaching_approach"] = "explain_in_simple_terms"
        context["check_understanding"] = True
        return context

    def _apply_active_recall(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """主动回忆策略"""
        context["recall_prompts"] = True
        context["test_before_review"] = True
        return context

    def _apply_interleaving(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """交错练习策略"""
        context["mix_topics"] = True
        context["alternate_problem_types"] = True
        return context

    def _apply_dual_coding(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """双重编码策略"""
        context["visual_diagrams"] = True
        context["text_and_image"] = True
        return context

    def _apply_elaboration(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """精细加工策略"""
        context["examples_and_connections"] = True
        context["why_questions"] = True
        return context
