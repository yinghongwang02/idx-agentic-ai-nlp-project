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
            final_response = self._format_search_result(
                state.get("search_result")
            )

        elif route == "market":
            final_response = self._format_market_result(
                state.get("market_result")
            )

        elif route == "recommend":
            final_response = (
                self._format_recommendation_result(
                    state.get(
                        "recommendation_result"
                    )
                )
            )

        elif route == "knowledge":
            final_response = (
                self._format_knowledge_result(
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

    def _format_search_result(
        self,
        value: Any,
    ) -> str:
        """
        Convert the structured PropertySearchAdapter output into
        user-facing text while preserving the structured result in state.
        """

        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, dict):
            final_response = value.get(
                "final_response"
            )

            if isinstance(
                final_response,
                str,
            ):
                return final_response

        return self._stringify(value)


    def _format_knowledge_result(
        self,
        value: Any,
    ) -> str:
        """
        Display only the grounded answer.

        Sources and retrieval evidence remain available in
        state["knowledge_result"].
        """

        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, dict):
            answer = value.get("answer")

            if isinstance(answer, str):
                return answer

        return self._stringify(value)


    def _format_market_result(
        self,
        value: Any,
    ) -> str:
        """
        Convert MarketSummary into a concise user-facing summary.
        """

        if value is None:
            return ""

        if isinstance(value, str):
            return value

        # Preserve compatibility with lightweight test doubles.
        if isinstance(value, dict):
            return self._stringify(value)

        city = getattr(
            value,
            "city",
            None,
        )

        comp_count = getattr(
            value,
            "comp_count",
            None,
        )

        median_close_price = getattr(
            value,
            "median_close_price",
            None,
        )

        average_dom = getattr(
            value,
            "average_days_on_market",
            None,
        )

        sale_to_list = getattr(
            value,
            "average_sale_to_list_ratio",
            None,
        )

        average_ppsf = getattr(
            value,
            "average_price_per_sqft",
            None,
        )

        trend = getattr(
            value,
            "recent_trend",
            None,
        )

        if city is None:
            return self._stringify(value)

        lines = [
            f"Market summary for {city}:",
        ]

        if comp_count is not None:
            lines.append(
                f"- Recent comparable sales: "
                f"{comp_count}"
            )

        if median_close_price is not None:
            lines.append(
                "- Median close price: "
                f"${median_close_price:,.0f}"
            )

        if average_dom is not None:
            lines.append(
                "- Average days on market: "
                f"{average_dom:.1f}"
            )

        if sale_to_list is not None:
            lines.append(
                "- Average sale-to-list ratio: "
                f"{sale_to_list:.1%}"
            )

        if average_ppsf is not None:
            lines.append(
                "- Average price per square foot: "
                f"${average_ppsf:,.0f}"
            )

        if trend is not None:
            direction = getattr(
                trend,
                "direction",
                None,
            )

            price_change = getattr(
                trend,
                "median_price_change_pct",
                None,
            )

            if direction:
                lines.append(
                    f"- Recent market direction: "
                    f"{direction}"
                )

            if price_change is not None:
                lines.append(
                    "- Recent median price change: "
                    f"{price_change:+.1%}"
                )

        return "\n".join(lines)


    def _format_recommendation_result(
        self,
        value: Any,
    ) -> str:
        """
        Convert similar-home recommendation results into a concise list.

        Full similarity and sold-comp evidence remain available in
        state["recommendation_result"].
        """

        if value is None:
            return ""

        if isinstance(value, str):
            return value

        # Preserve compatibility with existing unit-test doubles.
        if isinstance(value, dict):
            return self._stringify(value)

        if not isinstance(value, list):
            return self._stringify(value)

        if not value:
            return (
                "No similar-home recommendations "
                "were found."
            )

        lines = [
            "Similar-home recommendations:",
        ]

        for rank, result in enumerate(
            value,
            start=1,
        ):
            if not isinstance(result, dict):
                lines.append(
                    f"{rank}. {result}"
                )
                continue

            listing = result.get("listing")

            if listing is None:
                lines.append(
                    f"{rank}. Recommendation available"
                )
                continue

            address = getattr(
                listing,
                "unparsed_address",
                None,
            ) or "Address unavailable"

            city = getattr(
                listing,
                "city",
                None,
            )

            price = getattr(
                listing,
                "list_price",
                None,
            )

            hybrid_score = result.get(
                "hybrid_similarity_score"
            )

            summary = f"{rank}. {address}"

            if city:
                summary += f", {city}"

            if price is not None:
                summary += f" — ${price:,.0f}"

            if hybrid_score is not None:
                summary += (
                    f" — similarity "
                    f"{hybrid_score:.2f}/100"
                )

            lines.append(summary)

        return "\n".join(lines)

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
            search_text = (
                self._format_search_result(
                    state.get(
                        "search_result"
                    )
                )
            )

            if search_text:
                sections.append(
                    "Property Search:\n"
                    f"{search_text}"
                )

        if "market" in routes:
            market_text = (
                self._format_market_result(
                    state.get(
                        "market_result"
                    )
                )
            )

            if market_text:
                sections.append(
                    "Market Analysis:\n"
                    f"{market_text}"
                )

        if "recommend" in routes:
            recommendation_text = (
                self._format_recommendation_result(
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
            knowledge_text = (
                self._format_knowledge_result(
                    state.get(
                        "knowledge_result"
                    )
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