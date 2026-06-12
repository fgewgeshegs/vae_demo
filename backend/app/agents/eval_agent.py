"""评估 Agent - 学习评估 + 策略调整信号

从学习行为、问答记录、学习进度等数据中分析学习者状态，
生成 5 维度评分、改进建议和策略调整信号。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select, func, and_

from app.core.database import async_session_factory
from app.core.llm_gateway import LLMGateway, LLMMessage
from app.models.evaluation import Evaluation
from app.models.student_profile import StudentProfile
from app.models.learning_behavior import LearningBehavior
from app.models.qa_record import QARecord
from app.models.study_path import StudyPath
from app.models.learning_resource import LearningResource
from app.prompts.eval_prompts import EVALUATION_PROMPT
from app.services.learning_strategies import LearningStrategyEngine, LearningStrategy
from loguru import logger


class EvalAgent:
    """学习评估 Agent - 分析学习数据并生成评估报告"""

    def __init__(self):
        self.llm = LLMGateway()
        self.strategy_engine = LearningStrategyEngine()

    async def process(self, state: dict) -> dict:
        """生成学习评估"""
        user_id = state["user_id"]
        course_id = state.get("course_id")

        try:
            # 1. 收集学习数据
            learning_data = await self._collect_learning_data(user_id, course_id)

            if learning_data["is_empty"]:
                return {
                    "type": "eval",
                    "message": (
                        "📊 学习评估\n\n"
                        "目前还没有足够的学习数据来生成评估报告。\n"
                        "建议你先完成一些学习活动：\n"
                        "1. 查看课程内容\n"
                        "2. 完成练习题\n"
                        "3. 在问答区提问\n\n"
                        "完成这些活动后再来查看评估吧！"
                    ),
                    "evaluation": None,
                }

            # 2. 调用 LLM 生成评估
            evaluation = await self._generate_evaluation(learning_data)

            # 3. 应用学习策略
            strategy_context = self._apply_strategies(evaluation, learning_data)

            # 4. 保存到数据库
            eval_record = await self._save_evaluation(
                user_id=user_id,
                course_id=course_id,
                evaluation=evaluation,
                strategy_signals=strategy_context,
            )

            # 5. 构建友好消息
            message = self._build_message(evaluation, strategy_context)

            return {
                "type": "eval",
                "message": message,
                "evaluation": {
                    "id": eval_record.id,
                    "scores": evaluation.get("scores", {}),
                    "suggestions": evaluation.get("suggestions", []),
                    "strategy_signals": strategy_context,
                    "created_at": eval_record.created_at.isoformat() if eval_record.created_at else None,
                },
            }

        except Exception as e:
            logger.error(f"EvalAgent 错误: {e}")
            return {
                "type": "eval",
                "message": f"评估生成失败：{str(e)}",
                "evaluation": None,
            }

    async def _collect_learning_data(self, user_id: int, course_id: int | None) -> dict:
        """收集用户学习数据"""
        async with async_session_factory() as db:
            # 行为统计数据
            behavior_count = 0
            action_type_counts = {}
            total_duration = 0

            behavior_query = select(LearningBehavior).where(
                LearningBehavior.user_id == user_id
            )
            result = await db.execute(behavior_query)
            behaviors = result.scalars().all()
            behavior_count = len(behaviors)

            for b in behaviors:
                action_type_counts[b.action_type] = action_type_counts.get(b.action_type, 0) + 1
                total_duration += (b.duration_seconds or 0)

            # 问答统计
            qa_query = select(QARecord).where(QARecord.user_id == user_id)
            if course_id:
                qa_query = qa_query.where(QARecord.course_id == course_id)
            result = await db.execute(qa_query.order_by(QARecord.created_at.desc()))
            qa_records = result.scalars().all()
            qa_count = len(qa_records)
            answered_count = sum(1 for r in qa_records if r.answer)

            # 学习进度
            path_query = select(StudyPath).where(
                StudyPath.user_id == user_id,
                StudyPath.is_active == True,
            )
            if course_id:
                path_query = path_query.where(StudyPath.course_id == course_id)
            result = await db.execute(path_query)
            active_paths = result.scalars().all()

            path_progresses = []
            for p in active_paths:
                path_progresses.append({
                    "path_id": p.id,
                    "progress": p.progress,
                    "nodes_count": len(p.path_data.get("nodes", [])),
                    "current_index": p.path_data.get("current_index", 0),
                })

            # 资源统计
            resource_query = select(func.count(LearningResource.id)).where(
                LearningResource.user_id == user_id
            )
            if course_id:
                resource_query = resource_query.where(LearningResource.course_id == course_id)
            result = await db.execute(resource_query)
            resource_count = result.scalar() or 0

            # 最近评估分数趋势
            recent_query = select(Evaluation).where(
                Evaluation.user_id == user_id
            ).order_by(Evaluation.created_at.desc()).limit(5)
            result = await db.execute(recent_query)
            recent_evals = result.scalars().all()
            score_trends = []
            for ev in reversed(recent_evals):
                score_trends.append({
                    "date": ev.created_at.isoformat() if ev.created_at else "",
                    "scores": ev.scores,
                })

            # 画像数据
            profile_result = await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == user_id)
            )
            profile = profile_result.scalar_one_or_none()
            profile_data = profile.profile_data if profile else {}

        # 识别活跃天数
        active_dates = set()
        for b in behaviors:
            if b.created_at:
                active_dates.add(b.created_at.date())
        active_days = len(active_dates)

        learning_data = {
            "is_empty": behavior_count == 0 and qa_count == 0 and resource_count == 0,
            "behavior": {
                "total_count": behavior_count,
                "action_types": action_type_counts,
                "total_duration_minutes": round(total_duration / 60, 1),
                "active_days": active_days,
            },
            "qa": {
                "total_count": qa_count,
                "answered_count": answered_count,
                "answer_rate": round(answered_count / qa_count * 100, 1) if qa_count > 0 else 0,
            },
            "progress": {
                "active_paths": len(active_paths),
                "path_details": path_progresses,
            },
            "resources": {
                "total_count": resource_count,
            },
            "score_trends": score_trends,
            "profile_summary": {
                "level": profile_data.get("knowledge_base", {}).get("level", "未知"),
                "gaps": profile_data.get("knowledge_gaps", []),
                "weak_points": profile_data.get("weak_points", []),
                "goals": profile_data.get("learning_goals", {}),
            },
        }

        return learning_data

    async def _generate_evaluation(self, learning_data: dict) -> dict:
        """调用 LLM 生成评估报告"""
        try:
            prompt = EVALUATION_PROMPT.format(
                learning_data=json.dumps(learning_data, ensure_ascii=False, indent=2)
            )

            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system_prompt=(
                    "你是一个学习评估专家。根据学习数据生成 JSON 格式的评估报告。\n"
                    "评分维度说明：\n"
                    "- knowledge_mastery (知识掌握): 基于学习进度、问答质量、资源使用\n"
                    "- learning_efficiency (学习效率): 基于时间投入与产出比\n"
                    "- engagement (学习投入): 基于活跃天数、行为次数、访问频率\n"
                    "- consistency (学习连贯性): 基于学习节奏的规律性\n"
                    "- improvement (进步幅度): 基于评估分数趋势\n\n"
                    "请输出严格的 JSON 格式，不要包含其他内容。"
                ),
                temperature=0.4,
                max_tokens=2048,
            )

            # 解析 JSON
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            evaluation = json.loads(content)

            # 确保所有必要字段存在
            if "scores" not in evaluation:
                evaluation["scores"] = {}
            if "suggestions" not in evaluation:
                evaluation["suggestions"] = []
            if "strategy_signals" not in evaluation:
                evaluation["strategy_signals"] = {}

            return evaluation

        except Exception as e:
            logger.error(f"LLM 评估生成失败，使用规则评估: {e}")
            return self._rule_based_evaluation(learning_data)

    def _rule_based_evaluation(self, learning_data: dict) -> dict:
        """基于规则的评估（LLM 失败时备用）"""
        behavior = learning_data.get("behavior", {})
        qa = learning_data.get("qa", {})
        progress = learning_data.get("progress", {})
        resources = learning_data.get("resources", {})

        # 知识掌握度：基于问答完成率和资源使用
        knowledge_mastery = min(100, int(
            qa.get("answer_rate", 0) * 0.4 +
            min(100, progress.get("active_paths", 0) * 20) * 0.3 +
            min(100, resources.get("total_count", 0) * 10) * 0.3
        ))

        # 学习效率
        total_minutes = behavior.get("total_duration_minutes", 0)
        if total_minutes > 0:
            efficiency = min(100, int(
                (qa.get("total_count", 0) * 10 + resources.get("total_count", 0) * 5) /
                max(1, total_minutes / 60) * 20
            ))
        else:
            efficiency = 30
        learning_efficiency = min(100, efficiency)

        # 学习投入
        active_days = behavior.get("active_days", 0)
        engagement = min(100, int(
            min(100, active_days * 15) * 0.4 +
            min(100, behavior.get("total_count", 0) * 5) * 0.3 +
            min(100, qa.get("total_count", 0) * 10) * 0.3
        ))

        # 学习连贯性
        if active_days <= 1:
            consistency = 30
        else:
            consistency = min(100, 50 + active_days * 10)

        # 进步幅度
        score_trends = learning_data.get("score_trends", [])
        if len(score_trends) >= 2:
            first = score_trends[0].get("scores", {})
            last = score_trends[-1].get("scores", {})
            first_avg = sum(first.values()) / max(len(first), 1) if first else 0
            last_avg = sum(last.values()) / max(len(last), 1) if last else 0
            improvement = min(100, max(0, int((last_avg - first_avg) + 50)))
        else:
            improvement = 50

        # 生成建议
        suggestions = []
        if knowledge_mastery < 60:
            suggestions.append("建议加强基础知识学习，回顾课程讲义和教材")
        if engagement < 50:
            suggestions.append("建议增加学习频率，每天保持一定的学习时间")
        if consistency < 40:
            suggestions.append("建议制定固定的学习计划，保持学习节奏的连贯性")
        if learning_efficiency < 50:
            suggestions.append("可以尝试使用费曼学习法，通过教授他人来加深理解")
        if improvement < 40:
            suggestions.append("建议回顾之前的错题和难点，有针对性地进行复习")

        if not suggestions:
            suggestions.append("学习状态良好，建议继续保持当前的学习节奏")
            suggestions.append("尝试挑战更难的知识点，拓展知识边界")
            suggestions.append("可以考虑将学到的知识应用到实际项目中")

        return {
            "scores": {
                "knowledge_mastery": knowledge_mastery,
                "learning_efficiency": learning_efficiency,
                "engagement": engagement,
                "consistency": consistency,
                "improvement": improvement,
            },
            "suggestions": suggestions[:5],
            "strategy_signals": {
                "adjust_pace": consistency < 50,
                "review_suggested": knowledge_mastery < 70,
                "difficulty_change": "easier" if knowledge_mastery < 40 else ("harder" if knowledge_mastery > 85 else "same"),
            },
        }

    def _apply_strategies(self, evaluation: dict, learning_data: dict) -> dict:
        """应用学习策略并生成策略调整信号"""
        scores = evaluation.get("scores", {})
        knowledge_mastery = scores.get("knowledge_mastery", 50)
        consistency = scores.get("consistency", 50)
        engagement = scores.get("engagement", 50)

        strategy_signals = {
            "adjust_pace": consistency < 50,
            "review_suggested": knowledge_mastery < 70,
            "difficulty_change": "same",
        }

        # 确定难度调整
        if knowledge_mastery < 40:
            strategy_signals["difficulty_change"] = "easier"
        elif knowledge_mastery > 85:
            strategy_signals["difficulty_change"] = "harder"

        # 应用间隔重复策略
        if knowledge_mastery < 70:
            strategy_context = self.strategy_engine.apply(
                LearningStrategy.SPACED_REPETITION, {}
            )
            strategy_signals["review_intervals"] = strategy_context.get("review_intervals", [1, 3, 7, 14, 30])

        # 应用费曼学习法
        if knowledge_mastery < 60:
            strategy_context = self.strategy_engine.apply(
                LearningStrategy.FEYNMAN_TECHNIQUE, {}
            )
            strategy_signals["feynman_suggested"] = True
            strategy_signals["teaching_approach"] = strategy_context.get("teaching_approach", "")

        # 应用主动回忆策略
        if engagement < 60:
            strategy_context = self.strategy_engine.apply(
                LearningStrategy.ACTIVE_RECALL, {}
            )
            strategy_signals["recall_suggested"] = True

        return strategy_signals

    async def _save_evaluation(
        self,
        user_id: int,
        course_id: int | None,
        evaluation: dict,
        strategy_signals: dict,
    ) -> Evaluation:
        """保存评估到数据库"""
        async with async_session_factory() as db:
            eval_record = Evaluation(
                user_id=user_id,
                course_id=course_id,
                scores=evaluation.get("scores", {}),
                suggestions=evaluation.get("suggestions", []),
                strategy_signals=strategy_signals,
                report_data={
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "dimensions": list(evaluation.get("scores", {}).keys()),
                    "method": "llm_hybrid",
                },
            )
            db.add(eval_record)
            await db.commit()
            await db.refresh(eval_record)
            return eval_record

    def _build_message(self, evaluation: dict, strategy_signals: dict) -> str:
        """构建友好的评估消息"""
        scores = evaluation.get("scores", {})
        suggestions = evaluation.get("suggestions", [])

        parts = ["📊 学习评估报告\n"]

        # 评分概览
        parts.append("【各维度得分】")
        score_labels = {
            "knowledge_mastery": "知识掌握",
            "learning_efficiency": "学习效率",
            "engagement": "学习投入",
            "consistency": "学习连贯性",
            "improvement": "进步幅度",
        }
        for key, label in score_labels.items():
            value = scores.get(key, 0)
            bar = "█" * (value // 10) + "░" * (10 - value // 10)
            parts.append(f"  {label}: {bar} {value}/100")

        # 平均分
        avg_score = sum(scores.values()) / max(len(scores), 1)
        parts.append(f"\n📈 综合评分: {avg_score:.1f}/100")

        # 策略建议
        if strategy_signals.get("review_suggested"):
            parts.append("🔄 建议安排复习计划")
        if strategy_signals.get("difficulty_change") == "easier":
            parts.append("📖 建议降低学习难度，夯实基础")
        elif strategy_signals.get("difficulty_change") == "harder":
            parts.append("🚀 基础扎实，建议挑战更高难度")

        # 改进建议
        if suggestions:
            parts.append("\n💡 改进建议")
            for i, s in enumerate(suggestions[:3], 1):
                parts.append(f"  {i}. {s}")

        parts.append("\n请前往「学习评估」页面查看详细报告。")
        return "\n".join(parts)
