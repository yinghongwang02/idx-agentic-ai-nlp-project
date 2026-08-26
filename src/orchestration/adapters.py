from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.agents.intent_agent import IntentAgent
from src.agents.market_agent import MarketAgent
from src.schemas.orchestrator_state_schema import (
    OrchestratorState,
)
from src.workflow.graph import (
    PropertySearchGraph,
)
from src.recommendation.hybrid_recommendation import (
    HybridRecommendationService,
)


ListingIdResolver = Callable[
    [str],
    str | None,
]


class PropertySearchAdapter:
    def __init__(
        self,
        workflow: PropertySearchGraph,
    ) -> None:
        self.workflow = workflow

    def __call__(
        self,
        state: OrchestratorState,
    ) -> dict[str, Any]:
        result = self.workflow.run(
            state["user_query"]
        )

        return {
            "final_response": result.get(
                "final_response",
                "",
            ),
            "recommendations": result.get(
                "recommendations",
                [],
            ),
            "blocked": result.get(
                "blocked",
                False,
            ),
            "error": result.get(
                "error"
            ),
        }


class MarketAdapter:
    def __init__(
        self,
        market_agent: MarketAgent,
        intent_agent: IntentAgent,
    ) -> None:
        self.market_agent = market_agent
        self.intent_agent = intent_agent

    def __call__(
        self,
        state: OrchestratorState,
    ) -> Any:
        intent = self.intent_agent.run(
            state["user_query"]
        )

        if not intent.city:
            raise ValueError(
                "Market analysis requires a city."
            )

        return self.market_agent.run(
            city=intent.city,
        )


class RecommendationAdapter:
    def __init__(
        self,
        service: HybridRecommendationService,
        listing_id_resolver: ListingIdResolver,
    ) -> None:
        self.service = service
        self.listing_id_resolver = (
            listing_id_resolver
        )

    def __call__(
        self,
        state: OrchestratorState,
    ) -> Any:
        listing_id = (
            self.listing_id_resolver(
                state["user_query"]
            )
        )

        if listing_id is None:
            raise ValueError(
                "Similar-home recommendation "
                "requires a target listing ID."
            )

        return self.service.recommend(
            target_listing_id=listing_id,
            top_k=5,
        )


class KnowledgeAdapter:
    """
    Thin wrapper around the Week 8 knowledge RAG callable.

    Pass a callable that accepts the user query and returns the
    grounded knowledge result.
    """

    def __init__(
        self,
        answer_callable: Callable[
            [str],
            Any,
        ],
    ) -> None:
        self.answer_callable = (
            answer_callable
        )

    def __call__(
        self,
        state: OrchestratorState,
    ) -> Any:
        return self.answer_callable(
            state["user_query"]
        )