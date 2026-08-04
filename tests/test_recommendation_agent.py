from __future__ import annotations

import pytest

from src.agents.recommendation_agent import (
    RecommendationAgent,
)
from src.config.recommendation_config import (
    RecommendationConfig,
)
from src.schemas.comparable_value_analysis_schema import (
    ComparableValueAnalysis,
)
from src.schemas.listing_schema import ListingSchema
from src.schemas.negotiation_analysis_schema import (
    NegotiationAnalysis,
)
from src.schemas.preference_match_analysis_schema import (
    PreferenceMatchAnalysis,
)
from src.schemas.recommendation_score_schema import (
    RecommendationScore,
)


def make_listing(
    listing_key: str,
    address: str,
) -> ListingSchema:
    """
    Build a minimal valid listing for recommendation tests.
    """
    return ListingSchema(
        listing_key=listing_key,
        listing_id=listing_key,
        unparsed_address=address,
        city="Irvine",
        postal_code="92618",
        standard_status="Active",
        property_type="Residential",
        property_sub_type="SingleFamilyResidence",
        list_price=1_000_000,
        bedrooms_total=3,
        bathrooms_total_integer=2,
        living_area=1_800,
        association_fee=150.0,
        days_on_market=45,
        public_remarks=(
            "Updated home with a garage and community pool."
        ),
    )


def make_preference_analysis(
    score: float,
    *,
    signals: list[str] | None = None,
) -> PreferenceMatchAnalysis:
    """
    Build a real PreferenceMatchAnalysis object.
    """
    return PreferenceMatchAnalysis(
        preference_match_score=score,
        requested_preferences=[
            "pool",
            "view",
        ],
        matched_preferences=[
            "pool",
        ],
        unmatched_preferences=[
            "view",
        ],
        signals=(
            signals
            if signals is not None
            else [
                f"Preference score: {score:.0f}.",
            ]
        ),
    )


def make_comparable_value_analysis(
    score: float,
    *,
    signals: list[str] | None = None,
) -> ComparableValueAnalysis:
    """
    Build a real ComparableValueAnalysis object.

    The adjusted value score is the component consumed by
    RecommendationAgent.
    """
    return ComparableValueAnalysis(
        raw_value_score=score,
        comparable_quality_score=90.0,
        adjusted_value_score=score,
        asking_price_per_sqft=555.56,
        comparable_median_price_per_sqft=575.00,
        price_per_sqft_ratio=0.9662,
        match_level="strict",
        comp_count=10,
        valid_ppsf_count=9,
        ppsf_coverage_ratio=0.90,
        signals=(
            signals
            if signals is not None
            else [
                f"Comparable value score: {score:.0f}.",
            ]
        ),
    )


def make_negotiation_analysis(
    score: float,
    *,
    signals: list[str] | None = None,
) -> NegotiationAnalysis:
    """
    Build a real NegotiationAnalysis object.
    """
    return NegotiationAnalysis(
        negotiation_score=score,
        dom_score=score,
        sale_to_list_score=score,
        signals=(
            signals
            if signals is not None
            else [
                f"Negotiation score: {score:.0f}.",
            ]
        ),
    )


def make_recommendation(
    *,
    agent: RecommendationAgent,
    listing_key: str,
    score: float,
) -> RecommendationScore:
    """
    Build a recommendation where all three component scores are
    equal, making the resulting overall score equal to score
    regardless of the configured normalized weights.
    """
    return agent.score_listing(
        listing=make_listing(
            listing_key=listing_key,
            address=f"{listing_key} Test Street",
        ),
        preference_analysis=make_preference_analysis(
            score,
        ),
        comparable_value_analysis=(
            make_comparable_value_analysis(
                score,
            )
        ),
        negotiation_analysis=make_negotiation_analysis(
            score,
        ),
    )


def test_default_config_calculates_weighted_score() -> None:
    """
    Verify that the default configuration preserves the existing
    40% preference, 35% comparable-value, and 25% negotiation
    scoring policy.
    """
    agent = RecommendationAgent()

    recommendation = agent.score_listing(
        listing=make_listing(
            listing_key="TEST-001",
            address="1 Test Street",
        ),
        preference_analysis=make_preference_analysis(
            100.0,
        ),
        comparable_value_analysis=(
            make_comparable_value_analysis(
                80.0,
            )
        ),
        negotiation_analysis=make_negotiation_analysis(
            60.0,
        ),
    )

    expected_score = round(
        100.0 * agent.config.preference_weight
        + 80.0
        * agent.config.comparable_value_weight
        + 60.0
        * agent.config.negotiation_weight,
        2,
    )

    assert expected_score == 83.0

    assert recommendation.overall_score == expected_score
    assert recommendation.preference_match_score == 100.0
    assert recommendation.comparable_value_score == 80.0
    assert recommendation.negotiation_score == 60.0
    assert recommendation.recommendation_label == (
        "Strong Match"
    )


def test_custom_config_changes_weighted_score() -> None:
    """
    Verify that RecommendationAgent consumes injected weights
    rather than relying on hard-coded class constants.
    """
    config = RecommendationConfig(
        preference_weight=0.60,
        comparable_value_weight=0.20,
        negotiation_weight=0.20,
    )

    agent = RecommendationAgent(
        config=config,
    )

    recommendation = agent.score_listing(
        listing=make_listing(
            listing_key="TEST-002",
            address="2 Test Street",
        ),
        preference_analysis=make_preference_analysis(
            100.0,
        ),
        comparable_value_analysis=(
            make_comparable_value_analysis(
                80.0,
            )
        ),
        negotiation_analysis=make_negotiation_analysis(
            60.0,
        ),
    )

    expected_score = round(
        100.0 * 0.60
        + 80.0 * 0.20
        + 60.0 * 0.20,
        2,
    )

    assert expected_score == 88.0
    assert recommendation.overall_score == expected_score


def test_default_and_custom_configs_produce_different_scores(
) -> None:
    """
    Use the same listing-level signals to confirm that changing the
    scoring policy changes only the aggregation result.
    """
    listing = make_listing(
        listing_key="TEST-003",
        address="3 Test Street",
    )

    preference_analysis = make_preference_analysis(
        100.0,
    )

    comparable_value_analysis = (
        make_comparable_value_analysis(
            40.0,
        )
    )

    negotiation_analysis = make_negotiation_analysis(
        20.0,
    )

    default_agent = RecommendationAgent()

    custom_agent = RecommendationAgent(
        config=RecommendationConfig(
            preference_weight=0.20,
            comparable_value_weight=0.30,
            negotiation_weight=0.50,
        ),
    )

    default_result = default_agent.score_listing(
        listing=listing,
        preference_analysis=preference_analysis,
        comparable_value_analysis=(
            comparable_value_analysis
        ),
        negotiation_analysis=negotiation_analysis,
    )

    custom_result = custom_agent.score_listing(
        listing=listing,
        preference_analysis=preference_analysis,
        comparable_value_analysis=(
            comparable_value_analysis
        ),
        negotiation_analysis=negotiation_analysis,
    )

    assert default_result.overall_score == 59.0
    assert custom_result.overall_score == 42.0

    assert (
        default_result.overall_score
        != custom_result.overall_score
    )


def test_recommendation_agent_combines_reason_signals() -> None:
    """
    Verify that explanation signals preserve the expected domain
    order: preference, comparable value, then negotiation.
    """
    agent = RecommendationAgent()

    recommendation = agent.score_listing(
        listing=make_listing(
            listing_key="TEST-004",
            address="4 Test Street",
        ),
        preference_analysis=make_preference_analysis(
            100.0,
            signals=[
                "Pool preference matched.",
                "View preference not matched.",
            ],
        ),
        comparable_value_analysis=(
            make_comparable_value_analysis(
                75.0,
                signals=[
                    "Asking price per square foot is favorable.",
                ],
            )
        ),
        negotiation_analysis=make_negotiation_analysis(
            50.0,
            signals=[
                "Days on market suggests some flexibility.",
            ],
        ),
    )

    assert recommendation.reasons == [
        "Pool preference matched.",
        "View preference not matched.",
        "Asking price per square foot is favorable.",
        "Days on market suggests some flexibility.",
    ]


@pytest.mark.parametrize(
    (
        "score",
        "expected_label",
    ),
    [
        (100.0, "Strong Match"),
        (80.0, "Strong Match"),
        (79.99, "Good Match"),
        (65.0, "Good Match"),
        (64.99, "Moderate Match"),
        (50.0, "Moderate Match"),
        (49.99, "Limited Match"),
        (0.0, "Limited Match"),
    ],
)
def test_default_label_boundaries(
    score: float,
    expected_label: str,
) -> None:
    """
    Verify every boundary in the default four-level label policy.
    """
    agent = RecommendationAgent()

    assert (
        agent._get_recommendation_label(
            overall_score=score,
        )
        == expected_label
    )


def test_custom_thresholds_change_recommendation_labels(
) -> None:
    """
    Verify that label thresholds are read from the injected
    RecommendationConfig.
    """
    agent = RecommendationAgent(
        config=RecommendationConfig(
            strong_match_threshold=90.0,
            good_match_threshold=75.0,
            moderate_match_threshold=60.0,
        ),
    )

    assert (
        agent._get_recommendation_label(
            overall_score=95.0,
        )
        == "Strong Match"
    )

    assert (
        agent._get_recommendation_label(
            overall_score=85.0,
        )
        == "Good Match"
    )

    assert (
        agent._get_recommendation_label(
            overall_score=70.0,
        )
        == "Moderate Match"
    )

    assert (
        agent._get_recommendation_label(
            overall_score=55.0,
        )
        == "Limited Match"
    )


def test_score_listing_uses_custom_thresholds() -> None:
    """
    Verify threshold configuration through the public
    score_listing() behavior, not only the private label helper.
    """
    agent = RecommendationAgent(
        config=RecommendationConfig(
            strong_match_threshold=90.0,
            good_match_threshold=75.0,
            moderate_match_threshold=60.0,
        ),
    )

    recommendation = make_recommendation(
        agent=agent,
        listing_key="TEST-005",
        score=80.0,
    )

    assert recommendation.overall_score == 80.0
    assert recommendation.recommendation_label == (
        "Good Match"
    )


def test_recommendation_agent_ranks_highest_score_first(
) -> None:
    agent = RecommendationAgent()

    recommendations = [
        make_recommendation(
            agent=agent,
            listing_key="LOW",
            score=20.0,
        ),
        make_recommendation(
            agent=agent,
            listing_key="HIGH",
            score=100.0,
        ),
        make_recommendation(
            agent=agent,
            listing_key="MID",
            score=50.0,
        ),
    ]

    ranked = agent.rank(
        recommendations=recommendations,
        limit=3,
    )

    assert [
        item.listing.listing_key
        for item in ranked
    ] == [
        "HIGH",
        "MID",
        "LOW",
    ]


def test_recommendation_agent_uses_deterministic_tie_breaker(
) -> None:
    """
    Equal overall scores must be ordered by listing key so
    candidate completion order cannot affect parallel ranking.
    """
    agent = RecommendationAgent()

    recommendations = [
        make_recommendation(
            agent=agent,
            listing_key="LISTING-C",
            score=75.0,
        ),
        make_recommendation(
            agent=agent,
            listing_key="LISTING-A",
            score=75.0,
        ),
        make_recommendation(
            agent=agent,
            listing_key="LISTING-B",
            score=75.0,
        ),
    ]

    ranked = agent.rank(
        recommendations=recommendations,
        limit=3,
    )

    assert [
        item.listing.listing_key
        for item in ranked
    ] == [
        "LISTING-A",
        "LISTING-B",
        "LISTING-C",
    ]


def test_recommendation_agent_respects_rank_limit() -> None:
    agent = RecommendationAgent()

    recommendations = [
        make_recommendation(
            agent=agent,
            listing_key=f"TEST-{index}",
            score=float(index * 10),
        )
        for index in range(10)
    ]

    ranked = agent.rank(
        recommendations=recommendations,
        limit=5,
    )

    assert len(ranked) == 5

    assert [
        item.listing.listing_key
        for item in ranked
    ] == [
        "TEST-9",
        "TEST-8",
        "TEST-7",
        "TEST-6",
        "TEST-5",
    ]


def test_recommendation_agent_returns_structured_schema(
) -> None:
    """
    Confirm that score_listing returns the production
    RecommendationScore contract.
    """
    agent = RecommendationAgent()

    recommendation = make_recommendation(
        agent=agent,
        listing_key="TEST-STRUCTURED",
        score=70.0,
    )

    assert isinstance(
        recommendation,
        RecommendationScore,
    )

    assert recommendation.listing.listing_key == (
        "TEST-STRUCTURED"
    )

    assert recommendation.overall_score == 70.0
    assert recommendation.recommendation_label == (
        "Good Match"
    )