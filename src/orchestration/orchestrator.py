from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.schemas.orchestrator_state_schema import (
    OrchestratorState,
    RouterDecision,
)


CapabilityHandler = Callable[
    [OrchestratorState],
    Any,
]

RouterHandler = Callable[
    [str],
    RouterDecision,
]


class Orchestrator:
    """
    Week 9 top-level multi-agent orchestrator.

    Responsibilities:
    - classify the incoming user query;
    - route single-intent requests to one capability;
    - fan out mixed requests across multiple capabilities;
    - fan capability outputs back into one merge node.

    Business logic remains inside the existing specialized services.
    """

    def __init__(
        self,
        *,
        router: RouterHandler,
        search_handler: CapabilityHandler,
        market_handler: CapabilityHandler,
        recommendation_handler: CapabilityHandler,
        knowledge_handler: CapabilityHandler,
    ) -> None:
        self.router = router

        self.search_handler = search_handler
        self.market_handler = market_handler
        self.recommendation_handler = (
            recommendation_handler
        )
        self.knowledge_handler = knowledge_handler

        self.graph = self._build_graph()

    # ================================================================
    # Public interface
    # ================================================================

    def invoke(
        self,
        user_query: str,
        *,
        session_id: str | None = None,
    ) -> OrchestratorState:
        """
        Run the orchestration graph for one user request.
        """

        initial_state: OrchestratorState = {
            "user_query": user_query,
            "session_id": session_id,
            "agents_invoked": [],
            "errors": [],
        }

        return self.graph.invoke(
            initial_state
        )

    # ================================================================
    # Graph construction
    # ================================================================

    def _build_graph(self):
        builder = StateGraph(
            OrchestratorState
        )

        builder.add_node(
            "router",
            self._router_node,
        )

        builder.add_node(
            "search",
            self._search_node,
        )

        builder.add_node(
            "market",
            self._market_node,
        )

        builder.add_node(
            "recommend",
            self._recommend_node,
        )

        builder.add_node(
            "knowledge",
            self._knowledge_node,
        )

        builder.add_node(
            "merge",
            self._merge_node,
        )

        # START -> router
        builder.add_edge(
            START,
            "router",
        )

        # router -> one or more capability branches
        builder.add_conditional_edges(
            "router",
            self._route_capabilities,
            {
                "search": "search",
                "market": "market",
                "recommend": "recommend",
                "knowledge": "knowledge",
            },
        )

        # Fan-in
        builder.add_edge(
            "search",
            "merge",
        )

        builder.add_edge(
            "market",
            "merge",
        )

        builder.add_edge(
            "recommend",
            "merge",
        )

        builder.add_edge(
            "knowledge",
            "merge",
        )

        builder.add_edge(
            "merge",
            END,
        )

        return builder.compile()

    # ================================================================
    # Router
    # ================================================================

    def _router_node(
        self,
        state: OrchestratorState,
    ) -> dict[str, Any]:
        """
        Classify the user query and persist the routing decision.
        """

        decision = self.router(
            state["user_query"]
        )

        return {
            "route": decision.route,
            "routes": decision.routes,
            "route_reason": decision.reason,
        }

    def _route_capabilities(
        self,
        state: OrchestratorState,
    ) -> str | list[str]:
        """
        Dispatch one branch for single intent or multiple branches
        for mixed intent.

        LangGraph interprets a returned list as fan-out.
        """

        routes = state.get(
            "routes",
            [],
        )

        if not routes:
            raise ValueError(
                "Router returned no capability routes."
            )

        if len(routes) == 1:
            return routes[0]

        return routes

    # ================================================================
    # Search branch
    # ================================================================

    def _search_node(
        self,
        state: OrchestratorState,
    ) -> dict[str, Any]:
        try:
            result = self.search_handler(
                state
            )

            return {
                "search_result": result,
                "agents_invoked": [
                    "search",
                ],
            }

        except Exception as exc:
            return {
                "search_result": None,
                "agents_invoked": [
                    "search",
                ],
                "errors": [
                    self._format_error(
                        "search",
                        exc,
                    )
                ],
            }

    # ================================================================
    # Market branch
    # ================================================================

    def _market_node(
        self,
        state: OrchestratorState,
    ) -> dict[str, Any]:
        try:
            result = self.market_handler(
                state
            )

            return {
                "market_result": result,
                "agents_invoked": [
                    "market",
                ],
            }

        except Exception as exc:
            return {
                "market_result": None,
                "agents_invoked": [
                    "market",
                ],
                "errors": [
                    self._format_error(
                        "market",
                        exc,
                    )
                ],
            }

    # ================================================================
    # Recommendation branch
    # ================================================================

    def _recommend_node(
        self,
        state: OrchestratorState,
    ) -> dict[str, Any]:
        try:
            result = (
                self.recommendation_handler(
                    state
                )
            )

            return {
                "recommendation_result": (
                    result
                ),
                "agents_invoked": [
                    "recommend",
                ],
            }

        except Exception as exc:
            return {
                "recommendation_result": None,
                "agents_invoked": [
                    "recommend",
                ],
                "errors": [
                    self._format_error(
                        "recommend",
                        exc,
                    )
                ],
            }

    # ================================================================
    # Knowledge branch
    # ================================================================

    def _knowledge_node(
        self,
        state: OrchestratorState,
    ) -> dict[str, Any]:
        try:
            result = self.knowledge_handler(
                state
            )

            return {
                "knowledge_result": result,
                "agents_invoked": [
                    "knowledge",
                ],
            }

        except Exception as exc:
            return {
                "knowledge_result": None,
                "agents_invoked": [
                    "knowledge",
                ],
                "errors": [
                    self._format_error(
                        "knowledge",
                        exc,
                    )
                ],
            }

    # ================================================================
    # Merge / fan-in
    # ================================================================

    def _merge_node(
        self,
        state: OrchestratorState,
    ) -> dict[str, Any]:
        """
        Build one unified user-facing response after all dispatched
        capability branches have completed.
        """

        route = state["route"]

        if route == "search":
            final_response = (
                self._stringify(
                    state.get(
                        "search_result"
                    )
                )
            )

        elif route == "market":
            final_response = (
                self._stringify(
                    state.get(
                        "market_result"
                    )
                )
            )

        elif route == "recommend":
            final_response = (
                self._stringify(
                    state.get(
                        "recommendation_result"
                    )
                )
            )

        elif route == "knowledge":
            final_response = (
                self._stringify(
                    state.get(
                        "knowledge_result"
                    )
                )
            )

        elif route == "mixed":
            final_response = (
                self._merge_mixed_response(
                    state
                )
            )

        else:
            raise ValueError(
                f"Unsupported route: {route}"
            )

        errors = state.get(
            "errors",
            [],
        )

        if errors:
            final_response = (
                self._append_errors(
                    final_response,
                    errors,
                )
            )

        return {
            "final_response": final_response,
        }

    # ================================================================
    # Helpers
    # ================================================================

    @staticmethod
    def _stringify(
        value: Any,
    ) -> str:
        if value is None:
            return ""

        if isinstance(
            value,
            str,
        ):
            return value

        return str(value)

    def _merge_mixed_response(
        self,
        state: OrchestratorState,
    ) -> str:
        """
        Combine outputs from the branches selected by the router.

        The first Week 9 mixed case is Search + Market, but this method
        intentionally uses state["routes"] so the orchestration layer
        remains extensible.
        """

        sections: list[str] = []

        routes = state.get(
            "routes",
            [],
        )

        if "search" in routes:
            search_text = self._stringify(
                state.get(
                    "search_result"
                )
            )

            if search_text:
                sections.append(
                    "Property Search:\n"
                    f"{search_text}"
                )

        if "market" in routes:
            market_text = self._stringify(
                state.get(
                    "market_result"
                )
            )

            if market_text:
                sections.append(
                    "Market Analysis:\n"
                    f"{market_text}"
                )

        if "recommend" in routes:
            recommendation_text = (
                self._stringify(
                    state.get(
                        "recommendation_result"
                    )
                )
            )

            if recommendation_text:
                sections.append(
                    "Recommendations:\n"
                    f"{recommendation_text}"
                )

        if "knowledge" in routes:
            knowledge_text = self._stringify(
                state.get(
                    "knowledge_result"
                )
            )

            if knowledge_text:
                sections.append(
                    "Knowledge:\n"
                    f"{knowledge_text}"
                )

        if not sections:
            return (
                "No capability produced a usable response."
            )

        return "\n\n".join(
            sections
        )

    @staticmethod
    def _append_errors(
        response: str,
        errors: list[str],
    ) -> str:
        error_text = "\n".join(
            f"- {error}"
            for error in errors
        )

        if response:
            return (
                f"{response}\n\n"
                "Partial errors:\n"
                f"{error_text}"
            )

        return (
            "The request could not be fully completed.\n\n"
            "Errors:\n"
            f"{error_text}"
        )

    @staticmethod
    def _format_error(
        capability: str,
        exc: Exception,
    ) -> str:
        return (
            f"{capability}: "
            f"{type(exc).__name__}: "
            f"{exc}"
        )