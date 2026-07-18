from src.agents.market_agent import MarketAgent
from src.search.mysql_sold_comp_repository import MySQLSoldCompRepository


def main() -> None:
    repository = MySQLSoldCompRepository()
    agent = MarketAgent(repository=repository)

    city = "Irvine"

    summary = agent.run(
        city=city,
        months=12,
        limit=500,
    )

    print("=" * 80)
    print("MARKET AGENT TEST")
    print("=" * 80)

    print(f"City: {summary.city}")
    print(f"Postal Code: {summary.postal_code}")
    print(f"Comparable Count: {summary.comp_count}")

    print("-" * 80)

    print(
        f"Median Close Price: "
        f"${summary.median_close_price:,.2f}"
        if summary.median_close_price is not None
        else "Median Close Price: N/A"
    )

    print(
        f"Average Days on Market: "
        f"{summary.average_days_on_market:.2f}"
        if summary.average_days_on_market is not None
        else "Average Days on Market: N/A"
    )

    print(
        f"Average Sale-to-List Ratio: "
        f"{summary.average_sale_to_list_ratio:.4f}"
        if summary.average_sale_to_list_ratio is not None
        else "Average Sale-to-List Ratio: N/A"
    )

    print(
        f"Average Price per Sqft: "
        f"${summary.average_price_per_sqft:,.2f}"
        if summary.average_price_per_sqft is not None
        else "Average Price per Sqft: N/A"
    )

    print("=" * 80)
    print("MARKET AGENT TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()