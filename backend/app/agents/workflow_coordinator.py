"""Deterministic coordinator for explicit learning workflows."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from sqlalchemy import select

from app.agents.agent_protocol import agent_succeeded, normalize_agent_result
from app.agents.eval_agent import EvalAgent
from app.agents.path_agent import PathAgent
from app.agents.profile_agent import ProfileAgent
from app.core.database import async_session_factory
from app.models.evaluation import Evaluation
from app.models.learning_task import LearningTask
from app.models.student_profile import StudentProfile
from app.models.study_path import StudyPath

StepEmitter = Callable[[dict[str, Any]], Awaitable[None]]


class WorkflowCoordinator:
    """Run known task types through explicit agent workflows."""

    async def run(self, task: LearningTask, emit_step: StepEmitter | None = None) -> dict[str, Any]:
        if task.task_type == "generate_study_path":
            return await self.generate_study_path(task, emit_step=emit_step)
        if task.task_type == "update_profile":
            return await self.update_profile(task, emit_step=emit_step)
        if task.task_type == "generate_evaluation":
            return await self.generate_evaluation(task, emit_step=emit_step)
        if task.task_type == "generate_learning_resource":
            return await self.generate_learning_resource(task, emit_step=emit_step)
        raise ValueError(f"Unsupported learning task type: {task.task_type}")

    async def generate_study_path(
        self,
        task: LearningTask,
        emit_step: StepEmitter | None = None,
    ) -> dict[str, Any]:
        steps: list[dict[str, Any]] = []
        agent_results: list[dict[str, Any]] = []

        await self._emit(emit_step, "load_student_state", "running", "正在读取画像")
        state = await self._load_student_state(task)
        await self._emit(emit_step, "load_student_state", "done", "画像读取完成")
        steps.append({"name": "load_student_state", "status": "done"})

        profile_result = None
        profile_description = task.input.get("profile_description")
        if profile_description:
            await self._emit(emit_step, "profile_update", "running", "正在更新画像")
            profile_result = await ProfileAgent().process({
                "user_id": task.user_id,
                "course_id": task.course_id,
                "message": str(profile_description),
            })
            profile_agent_result = self._profile_agent_result(profile_result)
            agent_results.append(profile_agent_result)
            steps.append({
                "name": "profile_update",
                "status": "done" if agent_succeeded(profile_agent_result) else "failed",
            })
            state = await self._load_student_state(task)
            await self._emit(
                emit_step,
                "profile_update",
                "done" if agent_succeeded(profile_agent_result) else "failed",
                "画像更新完成" if agent_succeeded(profile_agent_result) else "画像更新失败",
                self._first_error(profile_agent_result),
            )
        else:
            steps.append({"name": "profile_summary", "status": "done"})

        await self._emit(emit_step, "latest_evaluation", "running", "正在分析最近评估")
        steps.append({
            "name": "latest_evaluation",
            "status": "done",
            "evaluation_id": (state.get("latest_evaluation") or {}).get("id"),
        })
        await self._emit(emit_step, "latest_evaluation", "done", "评估分析完成")

        await self._emit(emit_step, "path_agent", "running", "正在生成路径")
        path_result = await PathAgent().process({
            "user_id": task.user_id,
            "course_id": task.course_id,
            "message": self._message_for(task, "generate personalized study path"),
            "workflow_context": state,
        })
        path_agent_result = self._path_agent_result(path_result)
        agent_results.append(path_agent_result)
        steps.append({
            "name": "path_agent",
            "status": "done" if agent_succeeded(path_agent_result) else "failed",
        })
        await self._emit(
            emit_step,
            "path_agent",
            "done" if agent_succeeded(path_agent_result) else "failed",
            "路径生成完成" if agent_succeeded(path_agent_result) else "路径生成失败",
            self._first_error(path_agent_result),
        )

        if not agent_succeeded(path_agent_result):
            return {
                "status": "failed",
                "type": "path",
                "message": path_result.get("message", "学习路径生成失败"),
                "steps": steps + [{"name": "validate_result", "status": "failed"}],
                "artifacts": {},
                "agents": agent_results,
                "data": path_result,
            }

        resource_step = {"name": "resource_recommendations", "status": "skipped"}
        if task.input.get("generate_resources"):
            resource_step = await self._try_generate_recommended_resources(
                task,
                path_result,
                emit_step=emit_step,
            )
            if resource_step.get("agent_result"):
                agent_results.append(resource_step["agent_result"])
        steps.append(resource_step)

        await self._emit(emit_step, "save_result", "running", "正在保存结果")
        await self._emit(emit_step, "save_result", "done", "结果已保存")

        return {
            "status": "succeeded",
            "type": "path",
            "message": path_result.get("message", "学习路径生成成功"),
            "steps": steps + [{"name": "validate_result", "status": "done"}],
            "artifacts": {
                "path_id": path_result.get("path_id"),
                "evaluation_id": (state.get("latest_evaluation") or {}).get("id"),
                "resource_ids": resource_step.get("resource_ids", []),
            },
            "agents": agent_results,
            "data": {
                "profile": state.get("profile", {}),
                "profile_update": profile_result,
                "latest_evaluation": state.get("latest_evaluation"),
                "path": path_result,
            },
        }

    async def update_profile(
        self,
        task: LearningTask,
        emit_step: StepEmitter | None = None,
    ) -> dict[str, Any]:
        steps = [{"name": "load_student_state", "status": "done"}]
        await self._emit(emit_step, "load_student_state", "running", "正在读取画像")
        await self._load_student_state(task)
        await self._emit(emit_step, "load_student_state", "done", "画像读取完成")
        await self._emit(emit_step, "profile_agent", "running", "正在分析并更新画像")
        result = await ProfileAgent().process({
            "user_id": task.user_id,
            "course_id": task.course_id,
            "message": self._message_for(task, "update learner profile"),
        })
        agent_result = self._profile_agent_result(result)
        failed = not agent_succeeded(agent_result)
        await self._emit(
            emit_step,
            "profile_agent",
            "failed" if failed else "done",
            "画像更新失败" if failed else "画像更新完成",
            self._first_error(agent_result),
        )
        if not failed:
            await self._emit(emit_step, "save_result", "running", "正在保存结果")
            await self._emit(emit_step, "save_result", "done", "结果已保存")
        return {
            "status": "failed" if failed else "succeeded",
            "type": result.get("type", "profile_updated"),
            "message": result.get("error") if failed else "学习画像已更新",
            "steps": steps + [{"name": "profile_agent", "status": "failed" if failed else "done"}],
            "artifacts": {
                "profile_version": result.get("version"),
                "updated_fields": result.get("updated_fields", []),
                "insufficient_evidence": result.get("insufficient_evidence", []),
            },
            "agents": [agent_result],
            "data": result,
        }

    async def generate_evaluation(
        self,
        task: LearningTask,
        emit_step: StepEmitter | None = None,
    ) -> dict[str, Any]:
        steps = [{"name": "load_student_state", "status": "done"}]
        await self._emit(emit_step, "load_student_state", "running", "正在读取学习状态")
        await self._load_student_state(task)
        await self._emit(emit_step, "load_student_state", "done", "学习状态读取完成")
        await self._emit(emit_step, "eval_agent", "running", "正在分析评估")
        result = await EvalAgent().process({
            "user_id": task.user_id,
            "course_id": task.course_id,
            "message": self._message_for(task, "generate learning evaluation"),
        })
        agent_result = self._eval_agent_result(result)
        failed = not agent_succeeded(agent_result)
        evaluation = result.get("evaluation")
        await self._emit(
            emit_step,
            "eval_agent",
            "failed" if failed else "done",
            "评估生成失败" if failed else "评估生成完成",
            self._first_error(agent_result),
        )
        if not failed:
            await self._emit(emit_step, "save_result", "running", "正在保存结果")
            await self._emit(emit_step, "save_result", "done", "结果已保存")
        return {
            "status": "failed" if failed else "succeeded",
            "type": result.get("type", "eval"),
            "message": result.get("message", "评估生成完成"),
            "steps": steps + [{"name": "eval_agent", "status": "failed" if failed else "done"}],
            "artifacts": {"evaluation_id": evaluation.get("id") if evaluation else None},
            "agents": [agent_result],
            "data": result,
        }

    async def generate_learning_resource(
        self,
        task: LearningTask,
        emit_step: StepEmitter | None = None,
    ) -> dict[str, Any]:
        steps = [{"name": "load_student_state", "status": "done"}]
        await self._emit(emit_step, "load_student_state", "running", "正在读取学习状态")
        await self._load_student_state(task)
        await self._emit(emit_step, "load_student_state", "done", "学习状态读取完成")
        try:
            from app.agents.resource_agent import ResourceCoordinator
        except ModuleNotFoundError as exc:
            agent_result = normalize_agent_result(
                agent="ResourceCoordinator",
                raw={"type": "resource", "message": "资源生成工作流不可用"},
                type="learning_resource",
                success=False,
                errors=[{"message": str(exc)}],
            )
            return {
                "status": "failed",
                "type": "resource",
                "message": "资源生成工作流不可用：ResourceAgent 尚未实现或导入失败",
                "steps": steps + [{"name": "resource_agent", "status": "failed", "error": str(exc)}],
                "artifacts": {"resource_ids": []},
                "agents": [agent_result],
                "data": {},
            }

        await self._emit(emit_step, "resource_agent", "running", "正在生成资源")
        result = await ResourceCoordinator().process({
            "user_id": task.user_id,
            "course_id": task.course_id,
            "message": self._message_for(task, "generate learning resource"),
            "input": task.input,
        })
        agent_result = self._resource_agent_result(result)
        failed = not agent_succeeded(agent_result)
        resource_ids = [item["id"] for item in agent_result["artifacts"] if item.get("id")]
        await self._emit(
            emit_step,
            "resource_agent",
            "failed" if failed else "done",
            "资源生成失败" if failed else "资源生成完成",
            self._first_error(agent_result),
        )
        if not failed:
            await self._emit(emit_step, "save_result", "running", "正在保存结果")
            await self._emit(emit_step, "save_result", "done", "结果已保存")
        return {
            "status": "failed" if failed else "succeeded",
            "type": result.get("type", "resource"),
            "message": result.get("message", "资源生成完成"),
            "steps": steps + [{"name": "resource_agent", "status": "failed" if failed else "done"}],
            "artifacts": {"resource_ids": resource_ids},
            "agents": [agent_result],
            "data": result,
        }

    async def _load_student_state(self, task: LearningTask) -> dict[str, Any]:
        async with async_session_factory() as db:
            profile = (
                await db.execute(select(StudentProfile).where(StudentProfile.user_id == task.user_id))
            ).scalar_one_or_none()
            latest_evaluation = (
                await db.execute(
                    select(Evaluation)
                    .where(Evaluation.user_id == task.user_id)
                    .order_by(Evaluation.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            active_paths = (
                await db.execute(
                    select(StudyPath).where(
                        StudyPath.user_id == task.user_id,
                        StudyPath.is_active == True,
                    )
                )
            ).scalars().all()

        return {
            "profile": profile.profile_data if profile else {},
            "latest_evaluation": {
                "id": latest_evaluation.id,
                "scores": latest_evaluation.scores,
                "suggestions": latest_evaluation.suggestions,
                "strategy_signals": latest_evaluation.strategy_signals,
            } if latest_evaluation else None,
            "active_paths": [
                {
                    "id": path.id,
                    "course_id": path.course_id,
                    "progress": path.progress,
                    "current_index": path.path_data.get("current_index", 0),
                }
                for path in active_paths
            ],
        }

    async def _try_generate_recommended_resources(
        self,
        task: LearningTask,
        path_result: dict[str, Any],
        emit_step: StepEmitter | None = None,
    ) -> dict[str, Any]:
        try:
            from app.agents.resource_agent import ResourceCoordinator
        except ModuleNotFoundError as exc:
            agent_result = normalize_agent_result(
                agent="ResourceCoordinator",
                raw={"type": "resource", "message": "资源推荐工作流不可用"},
                type="learning_resource",
                success=False,
                errors=[{"message": str(exc)}],
            )
            return {
                "name": "resource_recommendations",
                "status": "skipped",
                "reason": str(exc),
                "agent_result": agent_result,
            }

        await self._emit(emit_step, "resource_recommendations", "running", "正在生成推荐资源")
        result = await ResourceCoordinator().process({
            "user_id": task.user_id,
            "course_id": task.course_id,
            "message": task.input.get("resource_request") or "generate resources for the new study path",
            "path_result": path_result,
        })
        agent_result = self._resource_agent_result(result)
        await self._emit(
            emit_step,
            "resource_recommendations",
            "done" if agent_succeeded(agent_result) else "failed",
            "推荐资源生成完成" if agent_succeeded(agent_result) else "推荐资源生成失败",
            self._first_error(agent_result),
        )
        return {
            "name": "resource_recommendations",
            "status": "done" if agent_succeeded(agent_result) else "failed",
            "resource_ids": [item["id"] for item in agent_result["artifacts"] if item.get("id")],
            "agent_result": agent_result,
        }

    def _profile_agent_result(self, result: dict[str, Any]) -> dict[str, Any]:
        return normalize_agent_result(
            agent="ProfileAgent",
            raw=result,
            type="student_profile",
            success=result.get("type") != "profile_error",
            artifacts=[
                {"type": "student_profile", "version": result.get("version")}
            ] if result.get("version") else [],
            errors=[{"message": result.get("error")}]
            if result.get("error") else [],
        )

    def _path_agent_result(self, result: dict[str, Any]) -> dict[str, Any]:
        return normalize_agent_result(
            agent="PathAgent",
            raw=result,
            type="study_path",
            success=bool(result.get("path_id")),
            artifacts=[
                {"type": "study_path", "id": result.get("path_id")}
            ] if result.get("path_id") else [],
            errors=[{"message": result.get("message", "study path generation failed")}]
            if not result.get("path_id") else [],
        )

    def _eval_agent_result(self, result: dict[str, Any]) -> dict[str, Any]:
        evaluation = result.get("evaluation")
        return normalize_agent_result(
            agent="EvalAgent",
            raw=result,
            type="evaluation",
            success=evaluation is not None,
            artifacts=[
                {"type": "evaluation", "id": evaluation.get("id")}
            ] if evaluation and evaluation.get("id") else [],
            errors=[{"message": result.get("message", "evaluation generation failed")}]
            if evaluation is None else [],
        )

    def _resource_agent_result(self, result: dict[str, Any]) -> dict[str, Any]:
        resource_ids = result.get("resource_ids") or []
        if not resource_ids and isinstance(result.get("resource"), dict) and result["resource"].get("id"):
            resource_ids = [result["resource"]["id"]]
        if not resource_ids and isinstance(result.get("resources"), list):
            resource_ids = [
                item["id"]
                for item in result["resources"]
                if isinstance(item, dict) and item.get("id")
            ]
        failed_type = result.get("type") in {"resource_error", "error"}
        return normalize_agent_result(
            agent="ResourceCoordinator",
            raw=result,
            type="learning_resource",
            success=bool(resource_ids) and not failed_type,
            artifacts=[
                {"type": "learning_resource", "id": resource_id}
                for resource_id in resource_ids
            ],
            errors=[{"message": result.get("message", "resource generation failed")}]
            if failed_type or not resource_ids else [],
        )

    async def _emit(
        self,
        emit_step: StepEmitter | None,
        name: str,
        status: str,
        label: str,
        error: str | None = None,
    ) -> None:
        if emit_step is None:
            return
        await emit_step({
            "name": name,
            "status": status,
            "label": label,
            "error": error,
        })

    def _first_error(self, agent_result: dict[str, Any]) -> str | None:
        errors = agent_result.get("errors")
        if not errors:
            return None
        first = errors[0]
        if isinstance(first, dict):
            return str(first.get("message")) if first.get("message") else None
        return str(first)

    def _message_for(self, task: LearningTask, fallback: str) -> str:
        text = task.input.get("message") or task.input.get("description") or task.input.get("request")
        return str(text) if text else fallback


workflow_coordinator = WorkflowCoordinator()

# Alias for callers that use action-oriented naming.
ActionCoordinator = WorkflowCoordinator
