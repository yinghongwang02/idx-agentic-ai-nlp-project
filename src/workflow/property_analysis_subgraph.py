from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from src.agents.comparable_value_agent import ComparableValueAgent
from src.agents.market_agent import MarketAgent
from src.agents.negotiation_agent import NegotiationAgent
from src.agents.preference_match_agent import PreferenceMatchAgent
from src.agents.recommendation_agent import RecommendationAgent
from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema


class PropertyAnalysisState(TypedDict, total=False):
    """
    State used by the single-listing property analysis subgraph.

    Each invocation analyzes exactly one active listing.
    """

    listing: ListingSchema
    intent: PropertyIntent

    market_context: Any
    preference_analysis: Any
    comparable_value_analysis: Any
    negotiation_analysis: Any

    recommendation: Any
    error: str | None


class PropertyAnalysisSubgraph:
    """
    Analyze one property through a reusable LangGraph subgraph.

    Workflow:
        Market context
        -> Preference matching
        -> Comparable value analysis
        -> Negotiation analysis
        -> Recommendation scoring

    This subgraph does not rank multiple listings. Ranking remains the
    responsibility of the parent PropertySearchGraph.
    """

    def __init__(
        self,
        market_agent: MarketAgent,
        preference_match_agent: PreferenceMatchAgent,
        comparable_value_agent: ComparableValueAgent,
        negotiation_agent: NegotiationAgent,
        recommendation_agent: RecommendationAgent,
    ) -> None:
        self.market_agent = market_agent
        self.preference_match_agent = preference_match_agent
        self.comparable_value_agent = comparable_value_agent
        self.negotiation_agent = negotiation_agent
        self.recommendation_agent = recommendation_agent

        self.graph = self._build_graph()

    def _build_graph(self):
        """
        Build and compile the single-property analysis graph.

        Parallel stages:

            START
            ├── Market Context
            └── Preference Analysis

            Market Context
            ├── Comparable Value Analysis
            └── Negotiation Analysis

            Preference + Comparable + Negotiation
            └── Recommendation Scoring
        """
        builder = StateGraph(PropertyAnalysisState)

        builder.add_node(
            "market_context",
            self._analyze_market_context,
        )

        builder.add_node(
            "preference_analysis",
            self._analyze_preferences,
        )

        builder.add_node(
            "comparable_value_analysis",
            self._analyze_comparable_value,
        )

        builder.add_node(
            "negotiation_analysis",
            self._analyze_negotiation,
        )

        builder.add_node(
            "recommendation_scoring",
            self._score_recommendation,
        )

        # Stage 1:
        # Market and preference analysis are independent.
        builder.add_edge(
            START,
            "market_context",
        )

        builder.add_edge(
            START,
            "preference_analysis",
        )

        # Stage 2:
        # Both analyses depend on market context,
        # but they do not depend on each other.
        builder.add_edge(
            "market_context",
            "comparable_value_analysis",
        )

        builder.add_edge(
            "market_context",
            "negotiation_analysis",
        )

        # Fan-in:
        # Recommendation scoring must wait until all three
        # analysis signals are available.
        builder.add_edge(
            [
                "preference_analysis",
                "comparable_value_analysis",
                "negotiation_analysis",
            ],
            "recommendation_scoring",
        )

        builder.add_edge(
            "recommendation_scoring",
            END,
        )

        return builder.compile()

    def run(
        self,
        listing: ListingSchema,
        intent: PropertyIntent,
    ) -> PropertyAnalysisState:
        """
        Analyze one listing and return its complete analysis state.
        """
        initial_state: PropertyAnalysisState = {
            "listing": listing,
            "intent": intent,
            "error": None,
        }

        return self.graph.invoke(initial_state)

    def _analyze_market_context(
        self,
        state: PropertyAnalysisState,
    ) -> dict[str, Any]:
        """
        Retrieve city-level and comparable-market context.
        """
        market_context = self.market_agent.analyze_listing(
            listing=state["listing"],
            months=12,
            market_limit=500,
            comparable_limit=100,
            minimum_comps=5,
        )

        return {
            "market_context": market_context,
        }

    def _analyze_preferences(
        self,
        state: PropertyAnalysisState,
    ) -> dict[str, Any]:
        """
        Measure how well the listing matches soft preferences.
        """
        preference_analysis = self.preference_match_agent.run(
            listing=state["listing"],
            intent=state["intent"],
        )

        return {
            "preference_analysis": preference_analysis,
        }

    def _analyze_comparable_value(
        self,
        state: PropertyAnalysisState,
    ) -> dict[str, Any]:
        """
        Compare the listing's asking value with similar sold comps.
        """
        comparable_value_analysis = (
            self.comparable_value_agent.run(
                listing=state["listing"],
                market_context=state["market_context"],
            )
        )

        return {
            "comparable_value_analysis": (
                comparable_value_analysis
            ),
        }

    def _analyze_negotiation(
        self,
        state: PropertyAnalysisState,
    ) -> dict[str, Any]:
        """
        Estimate negotiation opportunity using comparable-market signals.
        """
        negotiation_analysis = self.negotiation_agent.run(
            listing=state["listing"],
            market_context=state["market_context"],
        )

        return {
            "negotiation_analysis": negotiation_analysis,
        }

    def _score_recommendation(
        self,
        state: PropertyAnalysisState,
    ) -> dict[str, Any]:
        """
        Combine property-analysis signals into one recommendation score.
        """
        recommendation = (
            self.recommendation_agent.score_listing(
                listing=state["listing"],
                preference_analysis=state[
                    "preference_analysis"
                ],
                comparable_value_analysis=state[
                    "comparable_value_analysis"
                ],
                negotiation_analysis=state[
                    "negotiation_analysis"
                ],
            )
        )

        return {
            "recommendation": recommendation,
        }