from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.openclaw_runtime.skill_adapter import (
    RealEstateCopilotSkill,
)


@dataclass(frozen=True)
class RuntimeRequest:
    """
    Normalized inbound request understood by the runtime boundary.
    """

    message: str
    session_id: str | None = None
    channel: str = "local"


@dataclass(frozen=True)
class RuntimeResponse:
    """
    Normalized outbound result returned by the runtime.

    `raw_state` preserves the complete LangGraph orchestrator result so
    future communication layers can access structured search, market,
    recommendation, or knowledge evidence without changing the runtime.
    """

    text: str
    session_id: str | None
    channel: str

    route: str | None
    routes: tuple[str, ...]
    agents_invoked: tuple[str, ...]
    errors: tuple[str, ...]

    raw_state: dict[str, Any]


class OpenClawRuntime:
    """
    Thin OpenClaw-style execution boundary.

    This layer does not perform routing or business logic. It normalizes
    external requests, invokes a registered real-estate skill, and
    normalizes the resulting LangGraph state for downstream channels.
    """

    def __init__(
        self,
        skill: RealEstateCopilotSkill,
    ) -> None:
        self.skill = skill

    def handle(
        self,
        request: RuntimeRequest,
    ) -> RuntimeResponse:
        message = str(
            request.message or ""
        ).strip()

        if not message:
            raise ValueError(
                "Runtime request message cannot be empty."
            )

        state = self.skill.execute(
            message,
            session_id=request.session_id,
        )

        final_response = state.get(
            "final_response",
            "",
        )

        if final_response is None:
            final_response = ""

        return RuntimeResponse(
            text=str(final_response),
            session_id=request.session_id,
            channel=request.channel,
            route=state.get("route"),
            routes=tuple(
                state.get("routes", [])
            ),
            agents_invoked=tuple(
                state.get(
                    "agents_invoked",
                    [],
                )
            ),
            errors=tuple(
                state.get("errors", [])
            ),
            raw_state=state,
        )

    def handle_message(
        self,
        message: str,
        *,
        session_id: str | None = None,
        channel: str = "local",
    ) -> RuntimeResponse:
        """
        Convenience entry point for CLI, Streamlit, WhatsApp mock,
        or future API/channel integrations.
        """

        request = RuntimeRequest(
            message=message,
            session_id=session_id,
            channel=channel,
        )

        return self.handle(request)