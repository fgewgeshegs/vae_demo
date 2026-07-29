"""Coordinator for open-ended chat interactions."""

from __future__ import annotations

from app.agents.coordinator import CoordinatorAgent


class ChatCoordinator(CoordinatorAgent):
    """Open-ended conversation coordinator.

    This keeps LLM-guided tool selection scoped to chat only. Explicit button
    actions and learning tasks must go through WorkflowCoordinator.
    """


chat_coordinator = ChatCoordinator()
