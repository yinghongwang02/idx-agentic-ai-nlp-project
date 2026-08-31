from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from src.schemas.listing_schema import ListingSchema
from src.schemas.market_summary_schema import (
    MarketSummary,
)


EmailDraftStatus = Literal[
    "pending_approval",
]


@dataclass(frozen=True)
class EmailDraft:
    """
    Draft-only outbound email.

    Handbook safety rule:
    email must remain pending approval until an explicit
    human approval step authorizes outbound delivery.
    """

    to: str
    subject: str
    body: str
    status: EmailDraftStatus = "pending_approval"

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class EmailDraftAgent:
    """
    Build structured email drafts from existing real-estate
    application outputs.

    This agent never sends email.

    Supported MVP draft types:
    - property / recommendation digest
    - weekly market report

    Human approval and outbound delivery are handled by later
    workflow layers.
    """

    DEFAULT_DISCLAIMER = (
        "This summary is for informational purposes only. "
        "Property availability, pricing, and market conditions "
        "may change."
    )

    # =================================================================
    # Property / recommendation digest
    # =================================================================

    def draft_property_digest(
        self,
        *,
        to: str,
        listings: list[Any],
        market_summary: MarketSummary | None = None,
        buyer_preferences: str | None = None,
        max_listings: int = 5,
    ) -> EmailDraft:
        recipient = self._normalize_recipient(to)

        if max_listings <= 0:
            raise ValueError(
                "max_listings must be greater than zero."
            )

        normalized_listings = (
            self._normalize_listings(listings)
        )

        selected_listings = (
            normalized_listings[:max_listings]
        )

        city = self._resolve_digest_city(
            selected_listings,
            market_summary,
        )

        subject = self._build_digest_subject(
            city=city,
            listing_count=len(selected_listings),
        )

        body = self._build_digest_body(
            listings=selected_listings,
            market_summary=market_summary,
            buyer_preferences=buyer_preferences,
        )

        return EmailDraft(
            to=recipient,
            subject=subject,
            body=body,
            metadata={
                "draft_type": (
                    "property_recommendation_digest"
                ),
                "listing_count": len(
                    selected_listings
                ),
                "city": city,
            },
        )

    # =================================================================
    # Weekly market report
    # =================================================================

    def draft_weekly_market_report(
        self,
        *,
        to: str,
        market_summary: MarketSummary,
    ) -> EmailDraft:
        recipient = self._normalize_recipient(to)

        if market_summary is None:
            raise ValueError(
                "market_summary is required."
            )

        city = (
            market_summary.city
            or "your selected market"
        )

        subject = (
            f"Weekly Real Estate Market Report — {city}"
        )

        body = self._build_market_report_body(
            market_summary
        )

        return EmailDraft(
            to=recipient,
            subject=subject,
            body=body,
            metadata={
                "draft_type": (
                    "weekly_market_report"
                ),
                "city": market_summary.city,
                "comp_count": (
                    market_summary.comp_count
                ),
            },
        )

    # =================================================================
    # Digest formatting
    # =================================================================

    def _build_digest_subject(
        self,
        *,
        city: str | None,
        listing_count: int,
    ) -> str:
        if city:
            return (
                f"Property Recommendations in {city}"
            )

        if listing_count:
            return (
                "Your Property Recommendations"
            )

        return "Property Search Update"

    def _build_digest_body(
        self,
        *,
        listings: list[ListingSchema],
        market_summary: MarketSummary | None,
        buyer_preferences: str | None,
    ) -> str:
        lines = [
            "Hello,",
            "",
            (
                "Here is a summary of properties "
                "selected based on your search."
            ),
        ]

        normalized_preferences = str(
            buyer_preferences or ""
        ).strip()

        if normalized_preferences:
            lines.extend(
                [
                    "",
                    (
                        "Buyer preferences: "
                        f"{normalized_preferences}"
                    ),
                ]
            )

        lines.extend(
            [
                "",
                "Recommended Properties",
                "----------------------",
            ]
        )

        if listings:
            for rank, listing in enumerate(
                listings,
                start=1,
            ):
                lines.extend(
                    self._format_listing(
                        listing,
                        rank=rank,
                    )
                )

        else:
            lines.append(
                "No matching properties are currently available."
            )

        if market_summary is not None:
            lines.extend(
                [
                    "",
                    "Market Snapshot",
                    "---------------",
                ]
            )

            lines.extend(
                self._format_market_summary(
                    market_summary
                )
            )

        lines.extend(
            [
                "",
                self.DEFAULT_DISCLAIMER,
            ]
        )

        return "\n".join(lines)

    def _format_listing(
        self,
        listing: ListingSchema,
        *,
        rank: int,
    ) -> list[str]:
        lines = [
            "",
            (
                f"{rank}. "
                f"{listing.unparsed_address}, "
                f"{listing.city}"
            ),
            (
                f"   Price: "
                f"${listing.list_price:,.0f}"
            ),
        ]

        features: list[str] = []

        if listing.bedrooms_total is not None:
            features.append(
                f"{listing.bedrooms_total} beds"
            )

        if (
            listing.bathrooms_total_integer
            is not None
        ):
            features.append(
                (
                    f"{listing.bathrooms_total_integer} "
                    "baths"
                )
            )

        if listing.living_area is not None:
            features.append(
                f"{listing.living_area:,.0f} sqft"
            )

        if features:
            lines.append(
                "   " + " | ".join(features)
            )

        if listing.days_on_market is not None:
            lines.append(
                (
                    "   Days on market: "
                    f"{listing.days_on_market}"
                )
            )

        if listing.association_fee is not None:
            lines.append(
                (
                    "   HOA: "
                    f"${listing.association_fee:,.0f}"
                )
            )

        if listing.listing_id:
            lines.append(
                (
                    "   Listing ID: "
                    f"{listing.listing_id}"
                )
            )

        return lines

    # =================================================================
    # Market report formatting
    # =================================================================

    def _build_market_report_body(
        self,
        market_summary: MarketSummary,
    ) -> str:
        city = (
            market_summary.city
            or "Selected Market"
        )

        lines = [
            "Hello,",
            "",
            (
                f"Here is your weekly market report "
                f"for {city}."
            ),
            "",
            "Market Summary",
            "--------------",
        ]

        lines.extend(
            self._format_market_summary(
                market_summary
            )
        )

        trend = market_summary.recent_trend

        if trend is not None:
            lines.extend(
                [
                    "",
                    "Recent Trend",
                    "------------",
                ]
            )

            direction = getattr(
                trend,
                "direction",
                None,
            )

            price_change = getattr(
                trend,
                "median_price_change_pct",
                None,
            )

            dom_change = getattr(
                trend,
                "average_dom_change",
                None,
            )

            sale_to_list_change = getattr(
                trend,
                "sale_to_list_change",
                None,
            )

            if direction:
                lines.append(
                    (
                        "Market direction: "
                        f"{direction}"
                    )
                )

            if price_change is not None:
                lines.append(
                    (
                        "Median price change: "
                        f"{price_change:+.1%}"
                    )
                )

            if dom_change is not None:
                lines.append(
                    (
                        "Average DOM change: "
                        f"{dom_change:+.1f} days"
                    )
                )

            if sale_to_list_change is not None:
                lines.append(
                    (
                        "Sale-to-list change: "
                        f"{sale_to_list_change:+.2%}"
                    )
                )

        lines.extend(
            [
                "",
                self.DEFAULT_DISCLAIMER,
            ]
        )

        return "\n".join(lines)

    def _format_market_summary(
        self,
        market_summary: MarketSummary,
    ) -> list[str]:
        lines: list[str] = []

        if market_summary.comp_count is not None:
            lines.append(
                (
                    "Comparable sales analyzed: "
                    f"{market_summary.comp_count}"
                )
            )

        if (
            market_summary.median_close_price
            is not None
        ):
            lines.append(
                (
                    "Median close price: "
                    f"${market_summary.median_close_price:,.0f}"
                )
            )

        if (
            market_summary.average_days_on_market
            is not None
        ):
            lines.append(
                (
                    "Average days on market: "
                    f"{market_summary.average_days_on_market:.1f}"
                )
            )

        if (
            market_summary.average_sale_to_list_ratio
            is not None
        ):
            lines.append(
                (
                    "Average sale-to-list ratio: "
                    f"{market_summary.average_sale_to_list_ratio:.1%}"
                )
            )

        if (
            market_summary.average_price_per_sqft
            is not None
        ):
            lines.append(
                (
                    "Average price per square foot: "
                    f"${market_summary.average_price_per_sqft:,.0f}"
                )
            )

        return lines

    # =================================================================
    # Normalization helpers
    # =================================================================

    @staticmethod
    def _normalize_recipient(
        recipient: str,
    ) -> str:
        normalized = str(
            recipient or ""
        ).strip()

        if not normalized:
            raise ValueError(
                "Email recipient cannot be empty."
            )

        return normalized

    def _normalize_listings(
        self,
        listings: list[Any],
    ) -> list[ListingSchema]:
        normalized: list[
            ListingSchema
        ] = []

        for item in listings or []:
            listing = self._extract_listing(
                item
            )

            if listing is not None:
                normalized.append(listing)

        return normalized

    @staticmethod
    def _extract_listing(
        item: Any,
    ) -> ListingSchema | None:
        """
        Normalize listing-bearing result shapes used across the project.

        Supported inputs:
        - direct ListingSchema
        - RecommendationScore-like objects with `.listing`
        - recommendation dictionaries with {"listing": ListingSchema}
        """

        if isinstance(
            item,
            ListingSchema,
        ):
            return item

        # PropertySearchGraph recommendations are RecommendationScore-like
        # objects that preserve the underlying ListingSchema on `.listing`.
        object_listing = getattr(
            item,
            "listing",
            None,
        )

        if isinstance(
            object_listing,
            ListingSchema,
        ):
            return object_listing

        # Week 7 hybrid recommendation results use dictionary-shaped
        # records containing a ListingSchema under the "listing" key.
        if isinstance(item, dict):
            dict_listing = item.get(
                "listing"
            )

            if isinstance(
                dict_listing,
                ListingSchema,
            ):
                return dict_listing

        return None

    @staticmethod
    def _resolve_digest_city(
        listings: list[ListingSchema],
        market_summary: MarketSummary | None,
    ) -> str | None:
        if (
            market_summary is not None
            and market_summary.city
        ):
            return market_summary.city

        if listings:
            return listings[0].city

        return None