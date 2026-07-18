from src.agents.market_agent import MarketAgent
from src.agents.negotiation_agent import NegotiationAgent
from src.schemas.intent_schema import PropertyIntent
from src.search.mysql_search_repository import MySQLSearchRepository
from src.search.mysql_sold_comp_repository import MySQLSoldCompRepository


def main() -> None:
    search_repository = MySQLSearchRepository()
    sold_comp_repository = MySQLSoldCompRepository()

    market_agent = MarketAgent(
        repository=sold_comp_repository
    )

    negotiation_agent = NegotiationAgent()

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

    market_summary = market_agent.run(
        city="Irvine",
        months=12,
        limit=500,
    )

    print("=" * 80)
    print("NEGOTIATION AGENT TEST")
    print("=" * 80)

    print(
        f"Market Average DOM: "
        f"{market_summary.average_days_on_market:.2f}"
    )
    print(
        f"Market Sale-to-List Ratio: "
        f"{market_summary.average_sale_to_list_ratio:.4f}"
    )
    print(
        f"Market Median Close Price: "
        f"${market_summary.median_close_price:,.2f}"
    )

    for index, listing in enumerate(listings, start=1):
        analysis = negotiation_agent.run(
            listing=listing,
            market_summary=market_summary,
        )

        print("\n" + "-" * 80)
        print(f"Listing #{index}")
        print("-" * 80)

        print(f"Address: {listing.unparsed_address}")
        print(f"Price: ${listing.list_price:,.2f}")
        print(f"Days on Market: {listing.days_on_market}")
        print(f"HOA: {listing.association_fee}")

        print(
            f"Negotiation Score: "
            f"{analysis.negotiation_score:.2f}"
        )

        print(f"DOM Score: {analysis.dom_score:.2f}")
        print(
            f"Price Position Score: "
            f"{analysis.price_position_score:.2f}"
        )
        print(
            f"Sale-to-List Score: "
            f"{analysis.sale_to_list_score:.2f}"
        )
        print(f"HOA Score: {analysis.hoa_score:.2f}")

        print("Signals:")

        for signal in analysis.signals:
            print(f"- {signal}")

    print("\n" + "=" * 80)
    print("NEGOTIATION AGENT TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()