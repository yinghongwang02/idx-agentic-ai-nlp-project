from src.schemas.listing_schema import ListingSchema
from src.schemas.market_context_schema import MarketContext
from src.schemas.negotiation_analysis_schema import NegotiationAnalysis


class NegotiationAgent:
    """
    Estimate negotiation opportunity for an active listing.

    The analysis focuses on:
        1. Relative days on market
        2. Recent sale-to-list behavior

    Listing-specific comparable data is preferred.
    Broader city market data is used as a fallback.

    Higher scores indicate stronger evidence of potential
    negotiation leverage.
    """

    def run(
        self,
        listing: ListingSchema,
        market_context: MarketContext,
    ) -> NegotiationAnalysis:
        signals: list[str] = []

        comparable_market = (
            market_context.comparable_market
        )

        city_market = (
            market_context.city_market
        )

        use_comparable_market = (
            comparable_market.match_level
            != "market_fallback"
            and comparable_market.comp_count > 0
        )

        if use_comparable_market:
            reference_dom = (
                comparable_market
                .average_days_on_market
            )

            reference_sale_to_list = (
                comparable_market
                .average_sale_to_list_ratio
            )

            signals.append(
                f"Negotiation analysis uses "
                f"{comparable_market.comp_count} "
                f"{comparable_market.match_level} "
                f"comparable sales."
            )

        else:
            reference_dom = (
                city_market.average_days_on_market
            )

            reference_sale_to_list = (
                city_market
                .average_sale_to_list_ratio
            )

            signals.append(
                "Listing-specific comparable data was limited, "
                "so broader city market data is used."
            )

        dom_score = self._calculate_dom_score(
            listing=listing,
            reference_dom=reference_dom,
            signals=signals,
        )

        sale_to_list_score = (
            self._calculate_sale_to_list_score(
                reference_ratio=reference_sale_to_list,
                signals=signals,
            )
        )

        negotiation_score = (
            dom_score * 0.65
            + sale_to_list_score * 0.35
        )

        return NegotiationAnalysis(
            negotiation_score=round(
                negotiation_score,
                2,
            ),
            dom_score=round(
                dom_score,
                2,
            ),
            sale_to_list_score=round(
                sale_to_list_score,
                2,
            ),
            signals=signals,
        )

    @staticmethod
    def _calculate_dom_score(
        listing: ListingSchema,
        reference_dom: float | None,
        signals: list[str],
    ) -> float:
        listing_dom = listing.days_on_market

        if (
            listing_dom is None
            or reference_dom is None
            or reference_dom <= 0
        ):
            signals.append(
                "Days-on-market data was insufficient "
                "for a strong negotiation signal."
            )
            return 50.0

        ratio = listing_dom / reference_dom

        if ratio >= 2.0:
            signals.append(
                "The listing has been on the market much longer "
                "than comparable properties."
            )
            return 100.0

        if ratio >= 1.5:
            signals.append(
                "The listing has been on the market significantly "
                "longer than comparable properties."
            )
            return 85.0

        if ratio >= 1.2:
            signals.append(
                "The listing has been on the market longer "
                "than comparable properties."
            )
            return 70.0

        if ratio >= 0.8:
            signals.append(
                "The listing's market time is close "
                "to comparable properties."
            )
            return 50.0

        if ratio >= 0.4:
            signals.append(
                "The listing has been on the market for less time "
                "than comparable properties."
            )
            return 35.0

        signals.append(
            "The listing is relatively new compared "
            "with similar recent sales."
        )
        return 20.0

    @staticmethod
    def _calculate_sale_to_list_score(
        reference_ratio: float | None,
        signals: list[str],
    ) -> float:
        if reference_ratio is None:
            signals.append(
                "Sale-to-list data was insufficient "
                "for a strong negotiation signal."
            )
            return 50.0

        if reference_ratio < 0.95:
            signals.append(
                "Comparable properties have generally sold "
                "noticeably below asking price."
            )
            return 100.0

        if reference_ratio < 0.98:
            signals.append(
                "Comparable properties have generally sold "
                "below asking price."
            )
            return 80.0

        if reference_ratio < 1.00:
            signals.append(
                "Comparable properties have sold slightly below "
                "asking price on average."
            )
            return 60.0

        if reference_ratio <= 1.02:
            signals.append(
                "Comparable properties have sold close "
                "to asking price on average."
            )
            return 40.0

        signals.append(
            "Comparable properties have generally sold "
            "above asking price."
        )
        return 20.0