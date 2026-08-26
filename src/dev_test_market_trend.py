from src.agents.market_agent import MarketAgent
from src.search.mysql_sold_comp_repository import (
    MySQLSoldCompRepository,
)


def main() -> None:
    repository = MySQLSoldCompRepository()

    agent = MarketAgent(
        repository=repository
    )

    summary = agent.run(
        city="Pasadena"
    )

    print("=" * 80)
    print("MARKET TREND SMOKE TEST")
    print("=" * 80)

    print("City:", summary.city)
    print("12m comp count:", summary.comp_count)
    print(
        "12m median close price:",
        summary.median_close_price,
    )
    print()

    trend = summary.recent_trend

    assert trend is not None

    print("Anchor date:", trend.anchor_date)
    print(
        "Recent period:",
        trend.recent_start_date,
        "->",
        trend.recent_end_date,
    )
    print(
        "Previous period:",
        trend.previous_start_date,
        "->",
        trend.previous_end_date,
    )

    print()
    print("Recent comps:", trend.recent_comp_count)
    print("Previous comps:", trend.previous_comp_count)

    print()
    print(
        "Median price change:",
        trend.median_price_change_pct,
    )
    print(
        "Median PPSF change:",
        trend.median_ppsf_change_pct,
    )
    print(
        "Average DOM change:",
        trend.average_dom_change,
    )
    print(
        "Sale-to-list change:",
        trend.sale_to_list_change,
    )

    print()
    print("Direction:", trend.direction)

    print()
    print("PASS")


if __name__ == "__main__":
    main()