from __future__ import annotations

from typing import Any, Protocol


class OrchestratorLike(Protocol):
    """
    Minimal interface required by the OpenClaw skill adapter.

    Using a protocol keeps the runtime boundary independent from the
    concrete LangGraph implementation while remaining compatible with
    the existing Week 9 Orchestrator.
    """

    def invoke(
        self,
        user_query: str,
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        ...


class RealEstateCopilotSkill:
    """
    Thin OpenClaw-style skill adapter around the existing unified
    LangGraph orchestrator.

    Responsibilities:
    - accept a normalized runtime message;
    - delegate execution to the existing orchestrator;
    - return the orchestrator state unchanged.

    Routing, agent execution, fan-out/fan-in, and business logic remain
    inside the existing Week 9 orchestrator.
    """

    name = "real_estate_copilot"

    def __init__(
        self,
        orchestrator: OrchestratorLike,
    ) -> None:
        self.orchestrator = orchestrator

    def execute(
        self,
        message: str,
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        normalized_message = str(
            message or ""
        ).strip()

        if not normalized_message:
            raise ValueError(
                "Runtime message cannot be empty."
            )

        return self.orchestrator.invoke(
            normalized_message,
            session_id=session_id,
        )