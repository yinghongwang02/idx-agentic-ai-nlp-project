from src.schemas.listing_schema import ListingSchema
from src.schemas.market_summary_schema import MarketSummary
from src.schemas.negotiation_analysis_schema import NegotiationAnalysis


class NegotiationAgent:
    """
    Estimate negotiation opportunity for an active listing.

    The score is based on:
        - listing days on market
        - listing price relative to market median
        - recent market sale-to-list ratio
        - HOA burden

    Higher scores indicate stronger potential negotiation leverage.
    """

    def run(
        self,
        listing: ListingSchema,
        market_summary: MarketSummary,
    ) -> NegotiationAnalysis:
        signals: list[str] = []

        dom_score = self._calculate_dom_score(
            listing=listing,
            market_summary=market_summary,
            signals=signals,
        )

        price_position_score = self._calculate_price_position_score(
            listing=listing,
            market_summary=market_summary,
            signals=signals,
        )

        sale_to_list_score = self._calculate_sale_to_list_score(
            market_summary=market_summary,
            signals=signals,
        )

        hoa_score = self._calculate_hoa_score(
            listing=listing,
            signals=signals,
        )

        negotiation_score = (
            dom_score * 0.40
            + price_position_score * 0.30
            + sale_to_list_score * 0.20
            + hoa_score * 0.10
        )

        return NegotiationAnalysis(
            negotiation_score=round(negotiation_score, 2),
            dom_score=round(dom_score, 2),
            price_position_score=round(price_position_score, 2),
            sale_to_list_score=round(sale_to_list_score, 2),
            hoa_score=round(hoa_score, 2),
            signals=signals,
        )

    @staticmethod
    def _calculate_dom_score(
        listing: ListingSchema,
        market_summary: MarketSummary,
        signals: list[str],
    ) -> float:
        listing_dom = listing.days_on_market
        market_dom = market_summary.average_days_on_market

        if (
            listing_dom is None
            or market_dom is None
            or market_dom <= 0
        ):
            return 50.0

        ratio = listing_dom / market_dom

        if ratio >= 2.0:
            signals.append(
                "The listing has been on the market much longer than "
                "the recent market average."
            )
            return 100.0

        if ratio >= 1.5:
            signals.append(
                "The listing has been on the market significantly longer "
                "than the recent market average."
            )
            return 85.0

        if ratio >= 1.2:
            signals.append(
                "The listing has been on the market longer than the "
                "recent market average."
            )
            return 70.0

        if ratio >= 0.8:
            signals.append(
                "The listing's market time is close to the recent average."
            )
            return 50.0

        signals.append(
            "The listing is relatively new compared with the recent "
            "market average."
        )
        return 25.0

    @staticmethod
    def _calculate_price_position_score(
        listing: ListingSchema,
        market_summary: MarketSummary,
        signals: list[str],
    ) -> float:
        list_price = listing.list_price
        median_close_price = market_summary.median_close_price

        if (
            list_price is None
            or median_close_price is None
            or median_close_price <= 0
        ):
            return 50.0

        ratio = list_price / median_close_price

        if ratio >= 1.30:
            signals.append(
                "The listing price is well above the recent market median."
            )
            return 90.0

        if ratio >= 1.15:
            signals.append(
                "The listing price is above the recent market median."
            )
            return 75.0

        if ratio >= 0.90:
            signals.append(
                "The listing price is relatively close to the recent "
                "market median."
            )
            return 50.0

        signals.append(
            "The listing price is below the recent market median."
        )
        return 30.0

    @staticmethod
    def _calculate_sale_to_list_score(
        market_summary: MarketSummary,
        signals: list[str],
    ) -> float:
        ratio = market_summary.average_sale_to_list_ratio

        if ratio is None:
            return 50.0

        if ratio < 0.95:
            signals.append(
                "Recent homes have generally sold noticeably below "
                "their final asking prices."
            )
            return 100.0

        if ratio < 0.98:
            signals.append(
                "Recent homes have generally sold below their final "
                "asking prices."
            )
            return 80.0

        if ratio < 1.00:
            signals.append(
                "Recent homes have sold slightly below asking price "
                "on average."
            )
            return 60.0

        if ratio <= 1.02:
            signals.append(
                "Recent homes have sold close to asking price on average."
            )
            return 40.0

        signals.append(
            "Recent homes have generally sold above asking price."
        )
        return 20.0

    @staticmethod
    def _calculate_hoa_score(
        listing: ListingSchema,
        signals: list[str],
    ) -> float:
        hoa = listing.association_fee

        if hoa is None or hoa <= 0:
            return 50.0

        if hoa >= 1000:
            signals.append(
                "The property has a high HOA fee, which may reduce "
                "buyer demand."
            )
            return 85.0

        if hoa >= 500:
            signals.append(
                "The property has a relatively high HOA fee."
            )
            return 70.0

        if hoa >= 250:
            signals.append(
                "The property has a moderate HOA fee."
            )
            return 55.0

        return 40.0