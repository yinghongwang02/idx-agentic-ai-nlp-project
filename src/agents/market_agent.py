from statistics import mean, median

from src.schemas.market_summary_schema import MarketSummary
from src.search.sold_comp_repository import SoldCompRepository


class MarketAgent:
    """
    Calculate market-level metrics from recent sold comparable properties.

    Responsibility:
        - retrieve recent sold comps
        - calculate market metrics
        - return a normalized MarketSummary
    """

    def __init__(self, repository: SoldCompRepository) -> None:
        self.repository = repository

    def run(
        self,
        city: str,
        postal_code: str | None = None,
        months: int = 12,
        limit: int = 500,
    ) -> MarketSummary:
        comps = self.repository.find_recent_comps(
            city=city,
            postal_code=postal_code,
            months=months,
            limit=limit,
        )

        if not comps:
            return MarketSummary(
                city=city,
                postal_code=postal_code,
                comp_count=0,
            )

        close_prices = [
            comp.close_price
            for comp in comps
            if comp.close_price is not None
            and comp.close_price > 0
        ]

        days_on_market = [
            comp.days_on_market
            for comp in comps
            if comp.days_on_market is not None
            and comp.days_on_market >= 0
        ]

        sale_to_list_ratios = [
            comp.close_price / comp.list_price
            for comp in comps
            if comp.close_price is not None
            and comp.close_price > 0
            and comp.list_price is not None
            and comp.list_price > 0
        ]

        price_per_sqft_values = [
            comp.close_price / comp.living_area
            for comp in comps
            if comp.close_price is not None
            and comp.close_price > 0
            and comp.living_area is not None
            and comp.living_area > 0
        ]

        return MarketSummary(
            city=city,
            postal_code=postal_code,
            comp_count=len(comps),
            median_close_price=(
                median(close_prices)
                if close_prices
                else None
            ),
            average_days_on_market=(
                mean(days_on_market)
                if days_on_market
                else None
            ),
            average_sale_to_list_ratio=(
                mean(sale_to_list_ratios)
                if sale_to_list_ratios
                else None
            ),
            average_price_per_sqft=(
                mean(price_per_sqft_values)
                if price_per_sqft_values
                else None
            ),
        )