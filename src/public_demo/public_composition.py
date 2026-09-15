from __future__ import annotations

from typing import Any

from src.agents.intent_agent import IntentAgent
from src.agents.market_agent import MarketAgent
from src.agents.search_agent import SearchAgent
from src.orchestration.adapters import (
    MarketAdapter,
    PropertySearchAdapter,
)
from src.orchestration.orchestrator import Orchestrator
from src.orchestration.router import IntentRouter
from src.public_demo.demo_search_repository import (
    DemoSearchRepository,
)
from src.public_demo.demo_sold_comp_repository import (
    DemoSoldCompRepository,
)
from src.schemas.orchestrator_state_schema import (
    OrchestratorState,
)
from src.workflow.graph import PropertySearchGraph


def _recommendation_not_enabled(
    state: OrchestratorState,
) -> list[Any]:
    """
    Temporary public-demo handler.

    Replaced by the real HybridRecommendationService once the
    synthetic listing embedding artifacts are generated.
    """
    return []


def _knowledge_not_enabled(
    state: OrchestratorState,
) -> str:
    """
    Temporary public-demo handler.

    Replaced by the public-safe RAG capability once its knowledge
    artifacts are configured.
    """
    return (
        "The public knowledge assistant is being configured "
        "with portfolio-safe documents."
    )


def create_public_orchestrator() -> Orchestrator:
    """
    Build the public portfolio-demo orchestrator.

    Production business logic and orchestration are reused while
    private IDX data infrastructure is replaced with deterministic
    synthetic repositories.
    """

    # Public-safe repositories
    active_listing_repository = DemoSearchRepository()
    sold_comp_repository = DemoSoldCompRepository()

    # Property search
    search_agent = SearchAgent(
        repository=active_listing_repository,
    )

    property_search_workflow = PropertySearchGraph(
        search_agent=search_agent,
    )

    search_adapter = PropertySearchAdapter(
        workflow=property_search_workflow,
    )

    # Market analysis
    market_agent = MarketAgent(
        repository=sold_comp_repository,
    )

    market_intent_agent = IntentAgent(
        memory=None,
    )

    market_adapter = MarketAdapter(
        market_agent=market_agent,
        intent_agent=market_intent_agent,
    )

    # Top-level router + orchestrator
    router = IntentRouter()

    return Orchestrator(
        router=router.route,
        search_handler=search_adapter,
        market_handler=market_adapter,
        recommendation_handler=_recommendation_not_enabled,
        knowledge_handler=_knowledge_not_enabled,
    )