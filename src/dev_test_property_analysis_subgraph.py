from src.agents.comparable_value_agent import (
    ComparableValueAgent,
)
from src.agents.market_agent import MarketAgent
from src.agents.negotiation_agent import NegotiationAgent
from src.agents.preference_match_agent import (
    PreferenceMatchAgent,
)
from src.agents.recommendation_agent import (
    RecommendationAgent,
)
from src.schemas.intent_schema import PropertyIntent
from src.search.mysql_search_repository import (
    MySQLSearchRepository,
)
from src.search.mysql_sold_comp_repository import (
    MySQLSoldCompRepository,
)
from src.workflow.property_analysis_subgraph import (
    PropertyAnalysisSubgraph,
)


def main() -> None:
    intent = PropertyIntent(
        city="Irvine",
        min_bedrooms=3,
        property_type="SingleFamilyResidence",
        keywords=["garage"],
        preferences=["pool", "view"],
    )

    search_repository = MySQLSearchRepository()
    sold_comp_repository = MySQLSoldCompRepository()

    listings = search_repository.search(
        intent=intent,
        limit=1,
    )

    if not listings:
        print("No listings found.")
        return

    subgraph = PropertyAnalysisSubgraph(
        market_agent=MarketAgent(
            repository=sold_comp_repository,
        ),
        preference_match_agent=PreferenceMatchAgent(),
        comparable_value_agent=ComparableValueAgent(),
        negotiation_agent=NegotiationAgent(),
        recommendation_agent=RecommendationAgent(),
    )

    result = subgraph.run(
        listing=listings[0],
        intent=intent,
    )

    recommendation = result["recommendation"]

    print("=" * 80)
    print("PROPERTY ANALYSIS SUBGRAPH")
    print("=" * 80)
    print(
        f"Address: "
        f"{recommendation.listing.unparsed_address}"
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
        f"Overall Score: "
        f"{recommendation.overall_score:.2f}"
    )
    print(
        f"Label: "
        f"{recommendation.recommendation_label}"
    )

    assert result["market_context"] is not None
    assert result["preference_analysis"] is not None
    assert result["comparable_value_analysis"] is not None
    assert result["negotiation_analysis"] is not None
    assert result["recommendation"] is not None

    print("\nProperty Analysis Subgraph: PASS")


if __name__ == "__main__":
    main()