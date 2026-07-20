from src.schemas.comparable_value_analysis_schema import (
    ComparableValueAnalysis,
)
from src.schemas.listing_schema import ListingSchema
from src.schemas.market_context_schema import MarketContext


class ComparableValueAgent:
    """
    Evaluate whether an active listing appears attractively priced
    relative to similar recent sold properties.

    The final adjusted value score combines:
        - relative asking PPSF
        - comparable evidence quality

    Higher scores indicate stronger relative value.
    """

    def run(
        self,
        listing: ListingSchema,
        market_context: MarketContext,
    ) -> ComparableValueAnalysis:
        comparable_market = market_context.comparable_market

        signals: list[str] = []

        asking_ppsf = self._calculate_asking_ppsf(
            listing=listing,
        )

        comparable_ppsf = (
            comparable_market.median_price_per_sqft
        )

        raw_value_score, ppsf_ratio = (
            self._calculate_raw_value_score(
                asking_ppsf=asking_ppsf,
                comparable_ppsf=comparable_ppsf,
                signals=signals,
            )
        )

        valid_ppsf_count = self._estimate_valid_ppsf_count(
            comparable_market=comparable_market,
        )

        ppsf_coverage_ratio = (
            valid_ppsf_count
            / comparable_market.comp_count
            if comparable_market.comp_count > 0
            else 0.0
        )

        comparable_quality_score = (
            self._calculate_comparable_quality_score(
                match_level=comparable_market.match_level,
                comp_count=comparable_market.comp_count,
                ppsf_coverage_ratio=ppsf_coverage_ratio,
                signals=signals,
            )
        )

        adjusted_value_score = (
            self._adjust_value_score(
                raw_value_score=raw_value_score,
                comparable_quality_score=(
                    comparable_quality_score
                ),
            )
        )

        return ComparableValueAnalysis(
            raw_value_score=round(
                raw_value_score,
                2,
            ),
            comparable_quality_score=round(
                comparable_quality_score,
                2,
            ),
            adjusted_value_score=round(
                adjusted_value_score,
                2,
            ),
            asking_price_per_sqft=(
                round(asking_ppsf, 2)
                if asking_ppsf is not None
                else None
            ),
            comparable_median_price_per_sqft=(
                round(comparable_ppsf, 2)
                if comparable_ppsf is not None
                else None
            ),
            price_per_sqft_ratio=(
                round(ppsf_ratio, 4)
                if ppsf_ratio is not None
                else None
            ),
            match_level=comparable_market.match_level,
            comp_count=comparable_market.comp_count,
            valid_ppsf_count=valid_ppsf_count,
            ppsf_coverage_ratio=round(
                ppsf_coverage_ratio,
                4,
            ),
            signals=signals,
        )

    @staticmethod
    def _calculate_asking_ppsf(
        listing: ListingSchema,
    ) -> float | None:
        if (
            listing.list_price is None
            or listing.list_price <= 0
            or listing.living_area is None
            or listing.living_area <= 0
        ):
            return None

        return (
            listing.list_price
            / listing.living_area
        )

    @staticmethod
    def _calculate_raw_value_score(
        asking_ppsf: float | None,
        comparable_ppsf: float | None,
        signals: list[str],
    ) -> tuple[float, float | None]:
        if (
            asking_ppsf is None
            or comparable_ppsf is None
            or comparable_ppsf <= 0
        ):
            signals.append(
                "Price-per-square-foot data was insufficient "
                "for a strong value estimate."
            )
            return 50.0, None

        ratio = (
            asking_ppsf
            / comparable_ppsf
        )

        if ratio <= 0.85:
            signals.append(
                "The asking price per square foot is substantially "
                "below comparable sales."
            )
            return 100.0, ratio

        if ratio <= 0.90:
            signals.append(
                "The asking price per square foot is well below "
                "comparable sales."
            )
            return 90.0, ratio

        if ratio <= 0.95:
            signals.append(
                "The asking price per square foot is moderately "
                "below comparable sales."
            )
            return 80.0, ratio

        if ratio <= 0.98:
            signals.append(
                "The asking price per square foot is slightly "
                "below comparable sales."
            )
            return 65.0, ratio

        if ratio <= 1.02:
            signals.append(
                "The asking price per square foot is close "
                "to comparable sales."
            )
            return 50.0, ratio

        if ratio <= 1.05:
            signals.append(
                "The asking price per square foot is slightly "
                "above comparable sales."
            )
            return 40.0, ratio

        if ratio <= 1.10:
            signals.append(
                "The asking price per square foot is moderately "
                "above comparable sales."
            )
            return 30.0, ratio

        if ratio <= 1.20:
            signals.append(
                "The asking price per square foot is well above "
                "comparable sales."
            )
            return 15.0, ratio

        signals.append(
            "The asking price per square foot is substantially "
            "above comparable sales."
        )
        return 0.0, ratio

    @staticmethod
    def _calculate_comparable_quality_score(
        match_level: str,
        comp_count: int,
        ppsf_coverage_ratio: float,
        signals: list[str],
    ) -> float:
        match_level_scores = {
            "strict": 100.0,
            "relaxed": 80.0,
            "broad": 55.0,
            "market_fallback": 25.0,
        }

        match_score = match_level_scores.get(
            match_level,
            25.0,
        )

        if comp_count >= 20:
            count_score = 100.0
        elif comp_count >= 10:
            count_score = 85.0
        elif comp_count >= 5:
            count_score = 70.0
        elif comp_count > 0:
            count_score = 40.0
        else:
            count_score = 0.0

        coverage_score = max(
            0.0,
            min(
                ppsf_coverage_ratio * 100,
                100.0,
            ),
        )

        quality_score = (
            match_score * 0.50
            + count_score * 0.30
            + coverage_score * 0.20
        )

        signals.append(
            f"Comparable evidence quality is based on "
            f"{match_level} matching, "
            f"{comp_count} comparable sales, "
            f"and {ppsf_coverage_ratio:.0%} PPSF coverage."
        )

        return quality_score

    @staticmethod
    def _adjust_value_score(
        raw_value_score: float,
        comparable_quality_score: float,
    ) -> float:
        """
        Move the raw value score toward the neutral score of 50
        when comparable evidence quality is weaker.
        """

        confidence = (
            comparable_quality_score
            / 100
        )

        return (
            50.0
            + (
                raw_value_score
                - 50.0
            )
            * confidence
        )

    @staticmethod
    def _estimate_valid_ppsf_count(
        comparable_market,
    ) -> int:
        """
        Temporary approximation.

        ComparableSummary currently stores only aggregate metrics,
        not the exact number of comps with valid PPSF.

        Until that field is added to ComparableSummary, assume all
        matched comps contributed valid PPSF when a median PPSF exists.
        """

        if (
            comparable_market
            .median_price_per_sqft
            is None
        ):
            return 0

        return comparable_market.comp_count