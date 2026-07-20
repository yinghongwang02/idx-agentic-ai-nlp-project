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

        analysis = negotiation_agent.run(
            listing=listing,
            market_context=market_context,
        )

        comparable_market = (
            market_context.comparable_market
        )

        print("\n" + "-" * 100)
        print(f"Listing #{index}")
        print("-" * 100)

        print(
            f"Address: "
            f"{listing.unparsed_address}"
        )

        print(
            f"Match Level: "
            f"{comparable_market.match_level}"
        )

        print(
            f"Comparable Count: "
            f"{comparable_market.comp_count}"
        )

        print(
            f"Negotiation Score: "
            f"{analysis.negotiation_score:.2f}"
        )

        print(
            f"DOM Score: "
            f"{analysis.dom_score:.2f}"
        )

        print(
            f"Sale-to-List Score: "
            f"{analysis.sale_to_list_score:.2f}"
        )

        print("Signals:")

        for signal in analysis.signals:
            print(f"- {signal}")

    print("\n" + "=" * 80)
    print("NEGOTIATION AGENT TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()