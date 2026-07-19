from src.agents.market_agent import MarketAgent
from src.schemas.intent_schema import PropertyIntent
from src.search.mysql_search_repository import MySQLSearchRepository
from src.search.mysql_sold_comp_repository import MySQLSoldCompRepository


def main() -> None:
    search_repository = MySQLSearchRepository()
    sold_comp_repository = MySQLSoldCompRepository()

    market_agent = MarketAgent(
        repository=sold_comp_repository
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
    print("MARKET AGENT V2 TEST")
    print("=" * 100)

    for index, listing in enumerate(
        listings,
        start=1,
    ):
        context = market_agent.analyze_listing(
            listing=listing,
            months=12,
            market_limit=500,
            comparable_limit=100,
            minimum_comps=5,
        )

        city_market = context.city_market
        comparable_market = (
            context.comparable_market
        )

        print(f"\nLISTING #{index}")
        print("-" * 100)

        print(f"Address: {listing.unparsed_address}")
        print(f"Property Type: {listing.property_sub_type}")
        print(f"ZIP: {listing.postal_code}")
        print(f"List Price: ${listing.list_price:,.2f}")
        print(f"Living Area: {listing.living_area}")
        print(f"Days on Market: {listing.days_on_market}")

        print("\nCITY MARKET")
        print(
            f"Comp Count: "
            f"{city_market.comp_count}"
        )
        print(
            f"Median Close Price: "
            f"${city_market.median_close_price:,.2f}"
        )
        print(
            f"Average DOM: "
            f"{city_market.average_days_on_market:.2f}"
        )
        print(
            f"Sale-to-List Ratio: "
            f"{city_market.average_sale_to_list_ratio:.4f}"
        )
        print(
            f"Average PPSF: "
            f"${city_market.average_price_per_sqft:,.2f}"
        )

        print("\nCOMPARABLE MARKET")
        print(
            f"Match Level: "
            f"{comparable_market.match_level}"
        )
        print(
            f"Comp Count: "
            f"{comparable_market.comp_count}"
        )

        if (
            comparable_market.median_close_price
            is not None
        ):
            print(
                f"Median Close Price: "
                f"${comparable_market.median_close_price:,.2f}"
            )

        if (
            comparable_market.average_days_on_market
            is not None
        ):
            print(
                f"Average DOM: "
                f"{comparable_market.average_days_on_market:.2f}"
            )

        if (
            comparable_market.average_sale_to_list_ratio
            is not None
        ):
            print(
                f"Sale-to-List Ratio: "
                f"{comparable_market.average_sale_to_list_ratio:.4f}"
            )

        if (
            comparable_market.median_price_per_sqft
            is not None
        ):
            print(
                f"Median PPSF: "
                f"${comparable_market.median_price_per_sqft:,.2f}"
            )

    print("\n" + "=" * 100)
    print("MARKET AGENT V2 TEST COMPLETED")
    print("=" * 100)


if __name__ == "__main__":
    main()