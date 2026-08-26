from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, Field


RouteType = Literal[
    "search",
    "market",
    "recommend",
    "knowledge",
    "mixed",
]


class RouterDecision(BaseModel):
    """
    Deterministic routing decision for the top-level orchestrator.

    `route` is the primary handbook route.

    For single-intent requests:
        routes contains exactly one capability.

    For mixed requests:
        route == "mixed"
        routes contains the capabilities that should execute.
    """

    route: RouteType

    routes: list[
        Literal[
            "search",
            "market",
            "recommend",
            "knowledge",
        ]
    ] = Field(
        default_factory=list
    )

    reason: str = ""


class OrchestratorState(TypedDict, total=False):
    """
    Top-level state for Week 9 multi-agent orchestration.

    This state is intentionally separate from AgentState, which remains
    dedicated to the existing PropertySearchGraph.
    """

    # -----------------------------------------------------------------
    # Request
    # -----------------------------------------------------------------

    user_query: str
    session_id: str | None

    # -----------------------------------------------------------------
    # Routing
    # -----------------------------------------------------------------

    route: RouteType
    routes: list[str]
    route_reason: str

    # -----------------------------------------------------------------
    # Optional shared parsed information
    # -----------------------------------------------------------------

    parsed_intent: Any

    # -----------------------------------------------------------------
    # Capability outputs
    # -----------------------------------------------------------------

    search_result: Any
    market_result: Any
    recommendation_result: Any
    knowledge_result: Any

    # -----------------------------------------------------------------
    # Orchestration metadata
    # -----------------------------------------------------------------

    agents_invoked: Annotated[
        list[str],
        operator.add,
    ]

    # -----------------------------------------------------------------
    # Final response
    # -----------------------------------------------------------------

    final_response: str

    # -----------------------------------------------------------------
    # Observability / error state
    # -----------------------------------------------------------------

    latency_ms: float

    errors: Annotated[
        list[str],
        operator.add,
    ]