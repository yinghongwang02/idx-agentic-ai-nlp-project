from src.agents.comparable_value_agent import ComparableValueAgent
from src.agents.market_agent import MarketAgent
from src.agents.negotiation_agent import NegotiationAgent
from src.agents.preference_match_agent import PreferenceMatchAgent
from src.agents.recommendation_agent import RecommendationAgent
from src.schemas.intent_schema import PropertyIntent
from src.search.mysql_search_repository import MySQLSearchRepository
from src.search.mysql_sold_comp_repository import MySQLSoldCompRepository


def main() -> None:
    search_repository = MySQLSearchRepository()
    sold_comp_repository = MySQLSoldCompRepository()

    market_agent = MarketAgent(
        repository=sold_comp_repository,
    )
    preference_match_agent = PreferenceMatchAgent()
    comparable_value_agent = ComparableValueAgent()
    negotiation_agent = NegotiationAgent()
    recommendation_agent = RecommendationAgent()

    intent = PropertyIntent(
        city="Irvine",
        min_bedrooms=3,
        property_type="SingleFamilyResidence",
        keywords=["garage"],
        preferences=["pool", "view"],
    )

    # Keep the candidate pool larger than the final Top 5.
    listings = search_repository.search(
        intent=intent,
        limit=20,
    )

    if not listings:
        print("No active listings found.")
        return

    print("=" * 100)
    print("RECOMMENDATION AGENT INTEGRATION TEST")
    print("=" * 100)
    print(f"Candidate Listings: {len(listings)}")
    print(f"Requested Preferences: {intent.preferences}")

    scored_recommendations = []

    for index, listing in enumerate(listings, start=1):
        market_context = market_agent.analyze_listing(
            listing=listing,
            months=12,
            market_limit=500,
            comparable_limit=100,
            minimum_comps=5,
        )

        preference_analysis = preference_match_agent.run(
            listing=listing,
            intent=intent,
        )

        comparable_value_analysis = comparable_value_agent.run(
            listing=listing,
            market_context=market_context,
        )

        negotiation_analysis = negotiation_agent.run(
            listing=listing,
            market_context=market_context,
        )

        recommendation = recommendation_agent.score_listing(
            listing=listing,
            preference_analysis=preference_analysis,
            comparable_value_analysis=comparable_value_analysis,
            negotiation_analysis=negotiation_analysis,
        )

        scored_recommendations.append(recommendation)

        print("\n" + "-" * 100)
        print(f"CANDIDATE #{index}")
        print("-" * 100)
        print(f"Address: {listing.unparsed_address}")

        if listing.list_price is not None:
            print(f"Price: ${listing.list_price:,.0f}")
        else:
            print("Price: N/A")

        print(f"Days on Market: {listing.days_on_market}")
        print(
            f"Preference Match Score: "
            f"{recommendation.preference_match_score:.2f}"
        )
        print(
            f"Comparable Value Score: "
            f"{recommendation.comparable_value_score:.2f}"
        )
        print(
            f"Negotiation Score: "
            f"{recommendation.negotiation_score:.2f}"
        )
        print(
            f"Overall Recommendation Score: "
            f"{recommendation.overall_score:.2f}"
        )
        print(
            f"Recommendation Label: "
            f"{recommendation.recommendation_label}"
        )

    ranked_recommendations = recommendation_agent.rank(
        recommendations=scored_recommendations,
        limit=5,
    )

    print("\n" + "=" * 100)
    print("FINAL TOP 5 RECOMMENDATIONS")
    print("=" * 100)

    for rank, recommendation in enumerate(
        ranked_recommendations,
        start=1,
    ):
        listing = recommendation.listing

        print(f"\nRANK #{rank}")
        print("-" * 100)
        print(f"Address: {listing.unparsed_address}")
        print(
            f"Overall Score: "
            f"{recommendation.overall_score:.2f}"
        )
        print(
            f"Preference Match: "
            f"{recommendation.preference_match_score:.2f}"
        )
        print(
            f"Comparable Value: "
            f"{recommendation.comparable_value_score:.2f}"
        )
        print(
            f"Negotiation: "
            f"{recommendation.negotiation_score:.2f}"
        )
        print(
            f"Label: "
            f"{recommendation.recommendation_label}"
        )
        print("Reasons:")

        for reason in recommendation.reasons:
            print(f"- {reason}")

    assert len(ranked_recommendations) <= 5

    assert all(
        ranked_recommendations[index].overall_score
        >= ranked_recommendations[index + 1].overall_score
        for index in range(
            len(ranked_recommendations) - 1
        )
    ), (
        "Recommendation ranking is not "
        "sorted by overall score."
    )

    for recommendation in scored_recommendations:
        expected_score = round(
            recommendation.preference_match_score
            * recommendation_agent.PREFERENCE_WEIGHT
            + recommendation.comparable_value_score
            * recommendation_agent.COMPARABLE_VALUE_WEIGHT
            + recommendation.negotiation_score
            * recommendation_agent.NEGOTIATION_WEIGHT,
            2,
        )

        assert recommendation.overall_score == expected_score, (
            "Overall recommendation score "
            "does not match the configured weights."
        )

    print("\n" + "=" * 100)
    print(
        "PASS: Recommendation scores are "
        "calculated correctly."
    )
    print(
        "PASS: Final recommendations are "
        "ranked by overall score."
    )
    print(
        "RECOMMENDATION AGENT INTEGRATION "
        "TEST COMPLETED"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()