from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
import threading
import time

from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema
from src.workflow.property_analysis_subgraph import (
    PropertyAnalysisSubgraph,
)


@dataclass
class FakePreferenceAnalysis:
    score: float = 50.0


@dataclass
class FakeComparableValueAnalysis:
    adjusted_value_score: float = 75.0


@dataclass
class FakeNegotiationAnalysis:
    negotiation_score: float = 40.0


@dataclass
class FakeRecommendation:
    listing: ListingSchema
    preference_match_score: float
    comparable_value_score: float
    negotiation_score: float
    overall_score: float
    recommendation_label: str


class FakeMarketAgent:
    def __init__(self) -> None:
        self.call_count = 0
        self.received_listing: ListingSchema | None = None

    def analyze_listing(
        self,
        listing: ListingSchema,
        months: int,
        market_limit: int,
        comparable_limit: int,
        minimum_comps: int,
    ) -> dict[str, Any]:
        self.call_count += 1
        self.received_listing = listing

        assert months == 12
        assert market_limit == 500
        assert comparable_limit == 100
        assert minimum_comps == 5

        return {
            "comparable_market": {
                "median_close_price": 900_000,
                "average_days_on_market": 35.0,
            }
        }


class FakePreferenceMatchAgent:
    def __init__(self) -> None:
        self.call_count = 0
        self.received_listing: ListingSchema | None = None
        self.received_intent: PropertyIntent | None = None

    def run(
        self,
        listing: ListingSchema,
        intent: PropertyIntent,
    ) -> FakePreferenceAnalysis:
        self.call_count += 1
        self.received_listing = listing
        self.received_intent = intent

        return FakePreferenceAnalysis(
            score=50.0,
        )


class FakeComparableValueAgent:
    def __init__(self) -> None:
        self.call_count = 0
        self.received_listing: ListingSchema | None = None
        self.received_market_context: Any = None

    def run(
        self,
        listing: ListingSchema,
        market_context: Any,
    ) -> FakeComparableValueAnalysis:
        self.call_count += 1
        self.received_listing = listing
        self.received_market_context = market_context

        return FakeComparableValueAnalysis(
            adjusted_value_score=75.0,
        )


class FakeNegotiationAgent:
    def __init__(self) -> None:
        self.call_count = 0
        self.received_listing: ListingSchema | None = None
        self.received_market_context: Any = None

    def run(
        self,
        listing: ListingSchema,
        market_context: Any,
    ) -> FakeNegotiationAnalysis:
        self.call_count += 1
        self.received_listing = listing
        self.received_market_context = market_context

        return FakeNegotiationAnalysis(
            negotiation_score=40.0,
        )


class FakeRecommendationAgent:
    def __init__(self) -> None:
        self.call_count = 0
        self.received_listing: ListingSchema | None = None
        self.received_preference_analysis: Any = None
        self.received_comparable_value_analysis: Any = None
        self.received_negotiation_analysis: Any = None

    def score_listing(
        self,
        listing: ListingSchema,
        preference_analysis: FakePreferenceAnalysis,
        comparable_value_analysis: FakeComparableValueAnalysis,
        negotiation_analysis: FakeNegotiationAnalysis,
    ) -> FakeRecommendation:
        self.call_count += 1
        self.received_listing = listing
        self.received_preference_analysis = preference_analysis
        self.received_comparable_value_analysis = (
            comparable_value_analysis
        )
        self.received_negotiation_analysis = negotiation_analysis

        return FakeRecommendation(
            listing=listing,
            preference_match_score=preference_analysis.score,
            comparable_value_score=(
                comparable_value_analysis.adjusted_value_score
            ),
            negotiation_score=(
                negotiation_analysis.negotiation_score
            ),
            overall_score=55.0,
            recommendation_label="Moderate Match",
        )


class SlowMarketAgent:
    def __init__(
        self,
        barrier: threading.Barrier,
    ) -> None:
        self.barrier = barrier

    def analyze_listing(
        self,
        listing: ListingSchema,
        months: int,
        market_limit: int,
        comparable_limit: int,
        minimum_comps: int,
    ) -> dict[str, Any]:
        self.barrier.wait(timeout=2)

        time.sleep(0.05)

        return {
            "comparable_market": {
                "median_close_price": 900_000,
                "average_days_on_market": 35.0,
            }
        }


class SlowPreferenceMatchAgent:
    def __init__(
        self,
        barrier: threading.Barrier,
    ) -> None:
        self.barrier = barrier

    def run(
        self,
        listing: ListingSchema,
        intent: PropertyIntent,
    ) -> FakePreferenceAnalysis:
        self.barrier.wait(timeout=2)

        time.sleep(0.05)

        return FakePreferenceAnalysis(
            score=50.0,
        )


class ParallelComparableValueAgent:
    def __init__(
        self,
        barrier: threading.Barrier,
    ) -> None:
        self.barrier = barrier

    def run(
        self,
        listing: ListingSchema,
        market_context: Any,
    ) -> FakeComparableValueAnalysis:
        assert market_context is not None

        self.barrier.wait(timeout=2)

        time.sleep(0.05)

        return FakeComparableValueAnalysis(
            adjusted_value_score=75.0,
        )


class ParallelNegotiationAgent:
    def __init__(
        self,
        barrier: threading.Barrier,
    ) -> None:
        self.barrier = barrier

    def run(
        self,
        listing: ListingSchema,
        market_context: Any,
    ) -> FakeNegotiationAnalysis:
        assert market_context is not None

        self.barrier.wait(timeout=2)

        time.sleep(0.05)

        return FakeNegotiationAnalysis(
            negotiation_score=40.0,
        )
    

@pytest.fixture
def listing() -> ListingSchema:
    """
    Create one lightweight listing for subgraph testing.
    """
    return ListingSchema(
        listing_key="TEST-KEY-001",
        listing_id="TEST-001",
        unparsed_address="123 Test Street",
        city="Irvine",
        postal_code="92618",
        standard_status="Active",
        property_type="Residential",
        property_sub_type="SingleFamilyResidence",
        list_price=950_000,
        previous_list_price=975_000,
        bedrooms_total=3,
        bathrooms_total_integer=2,
        living_area=1_800,
        association_fee=150,
        days_on_market=45,
        latitude=33.6846,
        longitude=-117.8265,
        public_remarks=(
            "Updated home with a garage and community pool."
        ),
    )


@pytest.fixture
def intent() -> PropertyIntent:
    return PropertyIntent(
        city="Irvine",
        min_bedrooms=3,
        property_type="SingleFamilyResidence",
        keywords=["garage"],
        preferences=["pool", "view"],
    )


@pytest.fixture
def agents() -> dict[str, Any]:
    return {
        "market": FakeMarketAgent(),
        "preference": FakePreferenceMatchAgent(),
        "comparable": FakeComparableValueAgent(),
        "negotiation": FakeNegotiationAgent(),
        "recommendation": FakeRecommendationAgent(),
    }


@pytest.fixture
def subgraph(
    agents: dict[str, Any],
) -> PropertyAnalysisSubgraph:
    return PropertyAnalysisSubgraph(
        market_agent=agents["market"],
        preference_match_agent=agents["preference"],
        comparable_value_agent=agents["comparable"],
        negotiation_agent=agents["negotiation"],
        recommendation_agent=agents["recommendation"],
    )


def test_property_analysis_subgraph_returns_complete_analysis(
    subgraph: PropertyAnalysisSubgraph,
    listing: ListingSchema,
    intent: PropertyIntent,
) -> None:
    result = subgraph.run(
        listing=listing,
        intent=intent,
    )

    assert result["listing"] == listing
    assert result["intent"] == intent

    assert result["market_context"] is not None
    assert result["preference_analysis"] is not None
    assert result["comparable_value_analysis"] is not None
    assert result["negotiation_analysis"] is not None
    assert result["recommendation"] is not None

    assert result["error"] is None


def test_property_analysis_subgraph_calls_each_agent_once(
    subgraph: PropertyAnalysisSubgraph,
    listing: ListingSchema,
    intent: PropertyIntent,
    agents: dict[str, Any],
) -> None:
    subgraph.run(
        listing=listing,
        intent=intent,
    )

    assert agents["market"].call_count == 1
    assert agents["preference"].call_count == 1
    assert agents["comparable"].call_count == 1
    assert agents["negotiation"].call_count == 1
    assert agents["recommendation"].call_count == 1


def test_property_analysis_subgraph_passes_listing_and_intent(
    subgraph: PropertyAnalysisSubgraph,
    listing: ListingSchema,
    intent: PropertyIntent,
    agents: dict[str, Any],
) -> None:
    subgraph.run(
        listing=listing,
        intent=intent,
    )

    assert agents["market"].received_listing == listing

    assert agents["preference"].received_listing == listing
    assert agents["preference"].received_intent == intent

    assert agents["comparable"].received_listing == listing
    assert agents["negotiation"].received_listing == listing

    assert agents["recommendation"].received_listing == listing


def test_market_context_is_passed_to_dependent_agents(
    subgraph: PropertyAnalysisSubgraph,
    listing: ListingSchema,
    intent: PropertyIntent,
    agents: dict[str, Any],
) -> None:
    result = subgraph.run(
        listing=listing,
        intent=intent,
    )

    expected_market_context = result["market_context"]

    assert (
        agents["comparable"].received_market_context
        == expected_market_context
    )

    assert (
        agents["negotiation"].received_market_context
        == expected_market_context
    )


def test_analysis_results_are_passed_to_recommendation_agent(
    subgraph: PropertyAnalysisSubgraph,
    listing: ListingSchema,
    intent: PropertyIntent,
    agents: dict[str, Any],
) -> None:
    result = subgraph.run(
        listing=listing,
        intent=intent,
    )

    assert (
        agents["recommendation"].received_preference_analysis
        == result["preference_analysis"]
    )

    assert (
        agents[
            "recommendation"
        ].received_comparable_value_analysis
        == result["comparable_value_analysis"]
    )

    assert (
        agents["recommendation"].received_negotiation_analysis
        == result["negotiation_analysis"]
    )


def test_property_analysis_subgraph_returns_scored_recommendation(
    subgraph: PropertyAnalysisSubgraph,
    listing: ListingSchema,
    intent: PropertyIntent,
) -> None:
    result = subgraph.run(
        listing=listing,
        intent=intent,
    )

    recommendation = result["recommendation"]

    assert recommendation.listing == listing
    assert recommendation.preference_match_score == 50.0
    assert recommendation.comparable_value_score == 75.0
    assert recommendation.negotiation_score == 40.0
    assert recommendation.overall_score == 55.0
    assert recommendation.recommendation_label == "Moderate Match"


def test_market_and_preference_analysis_run_in_parallel(
    listing: ListingSchema,
    intent: PropertyIntent,
) -> None:
    """
    Verify that the independent first-stage branches execute
    concurrently.

    The barrier requires both nodes to begin execution before either
    node can continue. A sequential graph would time out.
    """
    barrier = threading.Barrier(2)

    subgraph = PropertyAnalysisSubgraph(
        market_agent=SlowMarketAgent(
            barrier=barrier,
        ),
        preference_match_agent=SlowPreferenceMatchAgent(
            barrier=barrier,
        ),
        comparable_value_agent=FakeComparableValueAgent(),
        negotiation_agent=FakeNegotiationAgent(),
        recommendation_agent=FakeRecommendationAgent(),
    )

    result = subgraph.run(
        listing=listing,
        intent=intent,
    )

    assert result["market_context"] is not None
    assert result["preference_analysis"] is not None
    assert result["recommendation"] is not None


def test_comparable_and_negotiation_run_in_parallel(
    listing: ListingSchema,
    intent: PropertyIntent,
) -> None:
    """
    Verify that comparable-value and negotiation analysis run
    concurrently after market context becomes available.
    """
    barrier = threading.Barrier(2)

    subgraph = PropertyAnalysisSubgraph(
        market_agent=FakeMarketAgent(),
        preference_match_agent=FakePreferenceMatchAgent(),
        comparable_value_agent=ParallelComparableValueAgent(
            barrier=barrier,
        ),
        negotiation_agent=ParallelNegotiationAgent(
            barrier=barrier,
        ),
        recommendation_agent=FakeRecommendationAgent(),
    )

    result = subgraph.run(
        listing=listing,
        intent=intent,
    )

    assert result["comparable_value_analysis"] is not None
    assert result["negotiation_analysis"] is not None
    assert result["recommendation"] is not None