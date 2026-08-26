from datetime import timedelta
from statistics import mean, median

from dateutil.relativedelta import relativedelta

from src.schemas.comparable_summary_schema import ComparableSummary
from src.schemas.listing_schema import ListingSchema
from src.schemas.market_context_schema import MarketContext
from src.schemas.market_summary_schema import MarketSummary
from src.schemas.market_trend_schema import MarketTrend
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
        Calculate broader city or ZIP-level market metrics
        together with a recent market trend.
        """

        comps = self.repository.find_recent_comps(
            city=city,
            postal_code=postal_code,
            months=months,
            limit=limit,
        )

        market_summary = self._build_market_summary(
            comps=comps,
            city=city,
            postal_code=postal_code,
        )

        latest_comps = self.repository.find_recent_comps(
            city=city,
            postal_code=postal_code,
            months=24,
            limit=1,
        )

        if not latest_comps:
            return market_summary

        anchor_date = latest_comps[0].close_date

        if anchor_date is None:
            return market_summary

        recent_end_date = anchor_date
        recent_start_date = (
            anchor_date
            - relativedelta(months=3)
        )

        previous_end_date = (
            recent_start_date
            - timedelta(days=1)
        )

        previous_start_date = (
            recent_start_date
            - relativedelta(months=3)
        )

        recent_comps = (
            self.repository.find_comps_by_date_range(
                city=city,
                start_date=recent_start_date,
                end_date=recent_end_date,
                postal_code=postal_code,
                limit=limit,
            )
        )

        previous_comps = (
            self.repository.find_comps_by_date_range(
                city=city,
                start_date=previous_start_date,
                end_date=previous_end_date,
                postal_code=postal_code,
                limit=limit,
            )
        )

        market_summary.recent_trend = (
            self._build_market_trend(
                recent_comps=recent_comps,
                previous_comps=previous_comps,
                anchor_date=anchor_date,
                recent_start_date=recent_start_date,
                recent_end_date=recent_end_date,
                previous_start_date=previous_start_date,
                previous_end_date=previous_end_date,
            )
        )

        return market_summary
    

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


    @staticmethod
    def _build_market_trend(
        recent_comps: list[SoldCompSchema],
        previous_comps: list[SoldCompSchema],
        anchor_date,
        recent_start_date,
        recent_end_date,
        previous_start_date,
        previous_end_date,
        minimum_period_comps: int = 10,
    ) -> MarketTrend:
        recent_close_prices = [
            comp.close_price
            for comp in recent_comps
            if comp.close_price is not None
            and comp.close_price > 0
        ]

        previous_close_prices = [
            comp.close_price
            for comp in previous_comps
            if comp.close_price is not None
            and comp.close_price > 0
        ]

        recent_ppsf = [
            comp.close_price / comp.living_area
            for comp in recent_comps
            if comp.close_price is not None
            and comp.close_price > 0
            and comp.living_area is not None
            and comp.living_area > 0
        ]

        previous_ppsf = [
            comp.close_price / comp.living_area
            for comp in previous_comps
            if comp.close_price is not None
            and comp.close_price > 0
            and comp.living_area is not None
            and comp.living_area > 0
        ]

        recent_dom = [
            comp.days_on_market
            for comp in recent_comps
            if comp.days_on_market is not None
            and comp.days_on_market >= 0
        ]

        previous_dom = [
            comp.days_on_market
            for comp in previous_comps
            if comp.days_on_market is not None
            and comp.days_on_market >= 0
        ]

        recent_sale_to_list = [
            comp.close_price / comp.list_price
            for comp in recent_comps
            if comp.close_price is not None
            and comp.close_price > 0
            and comp.list_price is not None
            and comp.list_price > 0
        ]

        previous_sale_to_list = [
            comp.close_price / comp.list_price
            for comp in previous_comps
            if comp.close_price is not None
            and comp.close_price > 0
            and comp.list_price is not None
            and comp.list_price > 0
        ]

        recent_median_price = (
            median(recent_close_prices)
            if recent_close_prices
            else None
        )

        previous_median_price = (
            median(previous_close_prices)
            if previous_close_prices
            else None
        )

        recent_median_ppsf = (
            median(recent_ppsf)
            if recent_ppsf
            else None
        )

        previous_median_ppsf = (
            median(previous_ppsf)
            if previous_ppsf
            else None
        )

        recent_average_dom = (
            mean(recent_dom)
            if recent_dom
            else None
        )

        previous_average_dom = (
            mean(previous_dom)
            if previous_dom
            else None
        )

        recent_average_sale_to_list = (
            mean(recent_sale_to_list)
            if recent_sale_to_list
            else None
        )

        previous_average_sale_to_list = (
            mean(previous_sale_to_list)
            if previous_sale_to_list
            else None
        )

        median_price_change_pct = (
            (recent_median_price - previous_median_price)
            / previous_median_price
            if recent_median_price is not None
            and previous_median_price is not None
            and previous_median_price > 0
            else None
        )

        median_ppsf_change_pct = (
            (recent_median_ppsf - previous_median_ppsf)
            / previous_median_ppsf
            if recent_median_ppsf is not None
            and previous_median_ppsf is not None
            and previous_median_ppsf > 0
            else None
        )

        average_dom_change = (
            recent_average_dom - previous_average_dom
            if recent_average_dom is not None
            and previous_average_dom is not None
            else None
        )

        sale_to_list_change = (
            recent_average_sale_to_list
            - previous_average_sale_to_list
            if recent_average_sale_to_list is not None
            and previous_average_sale_to_list is not None
            else None
        )

        direction = MarketAgent._classify_market_direction(
            recent_comp_count=len(recent_comps),
            previous_comp_count=len(previous_comps),
            minimum_period_comps=minimum_period_comps,
            median_price_change_pct=median_price_change_pct,
            median_ppsf_change_pct=median_ppsf_change_pct,
            average_dom_change=average_dom_change,
            sale_to_list_change=sale_to_list_change,
        )

        return MarketTrend(
            anchor_date=anchor_date,
            recent_start_date=recent_start_date,
            recent_end_date=recent_end_date,
            previous_start_date=previous_start_date,
            previous_end_date=previous_end_date,
            recent_comp_count=len(recent_comps),
            previous_comp_count=len(previous_comps),
            recent_median_close_price=recent_median_price,
            previous_median_close_price=previous_median_price,
            median_price_change_pct=median_price_change_pct,
            recent_median_price_per_sqft=recent_median_ppsf,
            previous_median_price_per_sqft=previous_median_ppsf,
            median_ppsf_change_pct=median_ppsf_change_pct,
            recent_average_days_on_market=recent_average_dom,
            previous_average_days_on_market=previous_average_dom,
            average_dom_change=average_dom_change,
            recent_average_sale_to_list_ratio=(
                recent_average_sale_to_list
            ),
            previous_average_sale_to_list_ratio=(
                previous_average_sale_to_list
            ),
            sale_to_list_change=sale_to_list_change,
            direction=direction,
        )

    @staticmethod
    def _classify_market_direction(
        recent_comp_count: int,
        previous_comp_count: int,
        minimum_period_comps: int,
        median_price_change_pct: float | None,
        median_ppsf_change_pct: float | None,
        average_dom_change: float | None,
        sale_to_list_change: float | None,
    ) -> str:
        if (
            recent_comp_count < minimum_period_comps
            or previous_comp_count < minimum_period_comps
        ):
            return "insufficient_data"

        score = 0
        valid_signals = 0

        if median_price_change_pct is not None:
            valid_signals += 1

            if median_price_change_pct >= 0.02:
                score += 1
            elif median_price_change_pct <= -0.02:
                score -= 1

        if median_ppsf_change_pct is not None:
            valid_signals += 1

            if median_ppsf_change_pct >= 0.02:
                score += 1
            elif median_ppsf_change_pct <= -0.02:
                score -= 1

        if average_dom_change is not None:
            valid_signals += 1

            if average_dom_change <= -5:
                score += 1
            elif average_dom_change >= 5:
                score -= 1

        if sale_to_list_change is not None:
            valid_signals += 1

            if sale_to_list_change >= 0.01:
                score += 1
            elif sale_to_list_change <= -0.01:
                score -= 1

        if valid_signals < 2:
            return "insufficient_data"

        if score >= 2:
            return "warming"

        if score <= -2:
            return "cooling"

        return "stable"