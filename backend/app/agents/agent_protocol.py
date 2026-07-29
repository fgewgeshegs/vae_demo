"""Shared output protocol for agent calls.

Agents in this codebase still return some legacy shapes. Workflow code should
normalize those shapes before making routing or success/failure decisions.
"""

from __future__ import annotations

from typing import Any


SUCCESS_STATUSES = {"success", "succeeded", "ok", "done"}
FAILED_STATUSES = {"failed", "error", "failure"}


def agent_result(
    *,
    agent: str,
    status: str,
    type: str,
    data: dict[str, Any] | None = None,
    state_updates: list[dict[str, Any]] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    next_actions: list[dict[str, Any]] | None = None,
    errors: list[dict[str, Any]] | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    """Build a result that follows the unified Agent output protocol."""

    normalized = {
        "agent": agent,
        "status": _normalize_status(status),
        "type": type,
        "data": data or {},
        "state_updates": state_updates or [],
        "artifacts": artifacts or [],
        "next_actions": next_actions or [],
        "errors": errors or [],
    }
    if message:
        normalized["message"] = message
    return normalized


def normalize_agent_result(
    *,
    agent: str,
    raw: dict[str, Any] | None,
    type: str | None = None,
    success: bool | None = None,
    state_updates: list[dict[str, Any]] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    next_actions: list[dict[str, Any]] | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Convert a legacy agent response into the unified Agent output protocol."""

    raw = raw or {}
    raw_status = raw.get("status")
    status = _status_from_success(success) if success is not None else _infer_status(raw_status, raw)
    result_type = type or raw.get("type") or "unknown"

    merged_errors = list(errors or [])
    raw_errors = raw.get("errors")
    if isinstance(raw_errors, list):
        merged_errors.extend(_coerce_error(item) for item in raw_errors)
    elif raw.get("error"):
        merged_errors.append({"message": str(raw["error"])})

    if status == "failed" and not merged_errors:
        message = raw.get("message") or "Agent failed"
        merged_errors.append({"message": str(message)})

    return agent_result(
        agent=agent,
        status=status,
        type=str(result_type),
        data=raw.get("data") if isinstance(raw.get("data"), dict) else raw,
        state_updates=state_updates or _list_of_dicts(raw.get("state_updates")),
        artifacts=artifacts or _list_of_dicts(raw.get("artifacts")),
        next_actions=next_actions or _list_of_dicts(raw.get("next_actions")),
        errors=merged_errors,
        message=raw.get("message"),
    )


def agent_succeeded(result: dict[str, Any]) -> bool:
    return result.get("status") == "success"


def _normalize_status(status: str) -> str:
    status_value = str(status or "").lower()
    if status_value in SUCCESS_STATUSES:
        return "success"
    if status_value in FAILED_STATUSES:
        return "failed"
    return "failed"


def _status_from_success(success: bool) -> str:
    return "success" if success else "failed"


def _infer_status(status: Any, raw: dict[str, Any]) -> str:
    if status is not None:
        return _normalize_status(str(status))
    result_type = str(raw.get("type", "")).lower()
    if result_type.endswith("_error") or result_type == "error":
        return "failed"
    if raw.get("error") or raw.get("errors"):
        return "failed"
    return "success"


def _coerce_error(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {"message": str(value)}


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
