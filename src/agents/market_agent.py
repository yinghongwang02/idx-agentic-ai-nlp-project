from statistics import mean, median

from src.schemas.comparable_summary_schema import ComparableSummary
from src.schemas.listing_schema import ListingSchema
from src.schemas.market_context_schema import MarketContext
from src.schemas.market_summary_schema import MarketSummary
from src.schemas.sold_comp_schema import SoldCompSchema
from src.search.sold_comp_repository import SoldCompRepository


class MarketAgent:
    """
    Calculate market-level and listing-specific comparable metrics.
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
        """
        Calculate broader city or ZIP-level market metrics.
        """

        comps = self.repository.find_recent_comps(
            city=city,
            postal_code=postal_code,
            months=months,
            limit=limit,
        )

        return self._build_market_summary(
            comps=comps,
            city=city,
            postal_code=postal_code,
        )

    def analyze_listing(
        self,
        listing: ListingSchema,
        months: int = 12,
        market_limit: int = 500,
        comparable_limit: int = 100,
        minimum_comps: int = 5,
    ) -> MarketContext:
        """
        Build both broader city market context and
        listing-specific comparable market context.
        """

        city_market = self.run(
            city=listing.city,
            months=months,
            limit=market_limit,
        )

        comparable_result = (
            self.repository.find_similar_comps(
                listing=listing,
                months=months,
                limit=comparable_limit,
                minimum_comps=minimum_comps,
            )
        )

        comparable_market = (
            self._build_comparable_summary(
                comps=comparable_result.comps,
                match_level=comparable_result.match_level,
            )
        )

        return MarketContext(
            city_market=city_market,
            comparable_market=comparable_market,
        )

    @staticmethod
    def _build_market_summary(
        comps: list[SoldCompSchema],
        city: str,
        postal_code: str | None,
    ) -> MarketSummary:
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

    @staticmethod
    def _build_comparable_summary(
        comps: list[SoldCompSchema],
        match_level: str,
    ) -> ComparableSummary:
        if not comps:
            return ComparableSummary(
                match_level=match_level,
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


        return ComparableSummary(
            match_level=match_level,
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
            median_price_per_sqft=(
                median(price_per_sqft_values)
                if price_per_sqft_values
                else None
            ),
            valid_ppsf_count=len(
                price_per_sqft_values
            ),
        )