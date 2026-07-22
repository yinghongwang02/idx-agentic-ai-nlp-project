from types import SimpleNamespace

from src.agents.recommendation_agent import RecommendationAgent
from src.schemas.listing_schema import ListingSchema


def make_listing(
    listing_key: str,
    address: str,
) -> ListingSchema:
    return ListingSchema(
        listing_key=listing_key,
        unparsed_address=address,
        city="Irvine",
        list_price=1_000_000,
    )


def make_preference_analysis(
    score: float,
) -> SimpleNamespace:
    return SimpleNamespace(
        preference_match_score=score,
        signals=[
            f"Preference score: {score:.0f}."
        ],
    )


def make_comparable_value_analysis(
    score: float,
) -> SimpleNamespace:
    return SimpleNamespace(
        adjusted_value_score=score,
        signals=[
            f"Comparable value score: {score:.0f}."
        ],
    )


def make_negotiation_analysis(
    score: float,
) -> SimpleNamespace:
    return SimpleNamespace(
        negotiation_score=score,
        signals=[
            f"Negotiation score: {score:.0f}."
        ],
    )


def test_recommendation_agent_calculates_weighted_score() -> None:
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
        100.0 * agent.PREFERENCE_WEIGHT
        + 80.0 * agent.COMPARABLE_VALUE_WEIGHT
        + 60.0 * agent.NEGOTIATION_WEIGHT,
        2,
    )

    assert recommendation.overall_score == expected_score
    assert recommendation.preference_match_score == 100.0
    assert recommendation.comparable_value_score == 80.0
    assert recommendation.negotiation_score == 60.0


def test_recommendation_agent_combines_reason_signals() -> None:
    agent = RecommendationAgent()

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
                75.0,
            )
        ),
        negotiation_analysis=make_negotiation_analysis(
            50.0,
        ),
    )

    assert recommendation.reasons == [
        "Preference score: 100.",
        "Comparable value score: 75.",
        "Negotiation score: 50.",
    ]


def test_recommendation_agent_ranks_highest_score_first() -> None:
    agent = RecommendationAgent()

    recommendations = [
        agent.score_listing(
            listing=make_listing(
                listing_key="LOW",
                address="Low Score Street",
            ),
            preference_analysis=make_preference_analysis(
                0.0,
            ),
            comparable_value_analysis=(
                make_comparable_value_analysis(
                    20.0,
                )
            ),
            negotiation_analysis=make_negotiation_analysis(
                20.0,
            ),
        ),
        agent.score_listing(
            listing=make_listing(
                listing_key="HIGH",
                address="High Score Street",
            ),
            preference_analysis=make_preference_analysis(
                100.0,
            ),
            comparable_value_analysis=(
                make_comparable_value_analysis(
                    100.0,
                )
            ),
            negotiation_analysis=make_negotiation_analysis(
                100.0,
            ),
        ),
        agent.score_listing(
            listing=make_listing(
                listing_key="MID",
                address="Mid Score Street",
            ),
            preference_analysis=make_preference_analysis(
                50.0,
            ),
            comparable_value_analysis=(
                make_comparable_value_analysis(
                    50.0,
                )
            ),
            negotiation_analysis=make_negotiation_analysis(
                50.0,
            ),
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


def test_recommendation_agent_respects_rank_limit() -> None:
    agent = RecommendationAgent()

    recommendations = []

    for index in range(10):
        recommendations.append(
            agent.score_listing(
                listing=make_listing(
                    listing_key=f"TEST-{index}",
                    address=f"{index} Test Street",
                ),
                preference_analysis=(
                    make_preference_analysis(
                        float(index * 10),
                    )
                ),
                comparable_value_analysis=(
                    make_comparable_value_analysis(
                        float(index * 10),
                    )
                ),
                negotiation_analysis=(
                    make_negotiation_analysis(
                        float(index * 10),
                    )
                ),
            )
        )

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


def test_recommendation_agent_assigns_expected_labels() -> None:
    agent = RecommendationAgent()

    cases = [
        (90.0, "Strong Match"),
        (70.0, "Good Match"),
        (55.0, "Moderate Match"),
        (30.0, "Limited Match"),
    ]

    for score, expected_label in cases:
        recommendation = agent.score_listing(
            listing=make_listing(
                listing_key=f"TEST-{score}",
                address=f"{score} Test Street",
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

        assert (
            recommendation.recommendation_label
            == expected_label
        )