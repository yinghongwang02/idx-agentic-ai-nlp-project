from src.agents.comparable_value_agent import (
    ComparableValueAgent,
)
from src.agents.market_agent import MarketAgent
from src.schemas.intent_schema import PropertyIntent
from src.search.mysql_search_repository import (
    MySQLSearchRepository,
)
from src.search.mysql_sold_comp_repository import (
    MySQLSoldCompRepository,
)


def main() -> None:
    search_repository = (
        MySQLSearchRepository()
    )

    sold_comp_repository = (
        MySQLSoldCompRepository()
    )

    market_agent = MarketAgent(
        repository=sold_comp_repository
    )

    value_agent = (
        ComparableValueAgent()
    )

    intent = PropertyIntent(
        city="Irvine",
        max_price=2000000,
        min_bedrooms=3,
    )

    listings = search_repository.search(
        intent=intent,
        limit=3,
    )

    if not listings:
        print("No active listings found.")
        return

    print("=" * 100)
    print("COMPARABLE VALUE AGENT TEST")
    print("=" * 100)

    for index, listing in enumerate(
        listings,
        start=1,
    ):
        market_context = (
            market_agent.analyze_listing(
                listing=listing,
                months=12,
                market_limit=500,
                comparable_limit=100,
                minimum_comps=5,
            )
        )

        analysis = value_agent.run(
            listing=listing,
            market_context=market_context,
        )

        print(
            f"\nLISTING #{index}"
        )

        print("-" * 100)

        print(
            f"Address: "
            f"{listing.unparsed_address}"
        )

        print(
            f"Match Level: "
            f"{analysis.match_level}"
        )

        print(
            f"Comparable Count: "
            f"{analysis.comp_count}"
        )

        print(
            f"Valid PPSF Count: "
            f"{analysis.valid_ppsf_count}"
        )

        print(
            f"PPSF Coverage: "
            f"{analysis.ppsf_coverage_ratio:.2%}"
        )

        if (
            analysis.asking_price_per_sqft
            is not None
        ):
            print(
                f"Asking PPSF: "
                f"${analysis.asking_price_per_sqft:,.2f}"
            )

        if (
            analysis
            .comparable_median_price_per_sqft
            is not None
        ):
            print(
                f"Comparable Median PPSF: "
                f"${analysis.comparable_median_price_per_sqft:,.2f}"
            )

        if (
            analysis.price_per_sqft_ratio
            is not None
        ):
            print(
                f"PPSF Ratio: "
                f"{analysis.price_per_sqft_ratio:.4f}"
            )

        print(
            f"Raw Value Score: "
            f"{analysis.raw_value_score:.2f}"
        )

        print(
            f"Comparable Quality Score: "
            f"{analysis.comparable_quality_score:.2f}"
        )

        print(
            f"Adjusted Value Score: "
            f"{analysis.adjusted_value_score:.2f}"
        )

        print("Signals:")

        for signal in analysis.signals:
            print(
                f"- {signal}"
            )

    print(
        "\n"
        + "=" * 100
    )

    print(
        "COMPARABLE VALUE AGENT "
        "TEST COMPLETED"
    )

    print(
        "=" * 100
    )


if __name__ == "__main__":
    main()