from src.schemas.intent_schema import PropertyIntent
from src.schemas.recommendation_score_schema import RecommendationScore


class ExplanationAgent:
    """
    Generate user-facing explanations for ranked property recommendations.
    """

    def run(
        self,
        intent: PropertyIntent,
        recommendations: list[RecommendationScore],
    ) -> str:
        if not recommendations:
            return "No matching listings found."

        lines = [
            "Top property recommendations based on your search criteria "
            "and recommendation signals:"
        ]

        for rank, recommendation in enumerate(
            recommendations,
            start=1,
        ):
            listing = recommendation.listing

            lines.append("")
            lines.append(
                f"{rank}. {listing.unparsed_address}"
            )

            details = self._build_listing_details(
                recommendation=recommendation,
            )

            if details:
                lines.append(
                    "   " + details
                )

            lines.append(
                f"   Recommendation: "
                f"{recommendation.recommendation_label} "
                f"({recommendation.overall_score:.2f}/100)"
            )

            lines.append(
                "   Score breakdown: "
                f"Preference match "
                f"{recommendation.preference_match_score:.2f}, "
                f"Comparable value "
                f"{recommendation.comparable_value_score:.2f}, "
                f"Negotiation opportunity "
                f"{recommendation.negotiation_score:.2f}."
            )

            search_reasons = (
                self._build_search_match_reasons(
                    intent=intent,
                    recommendation=recommendation,
                )
            )

            if search_reasons:
                lines.append(
                    "   Search match: "
                    + "; ".join(search_reasons)
                    + "."
                )

            if recommendation.reasons:
                lines.append(
                    "   Why it ranked here:"
                )

                for reason in recommendation.reasons:
                    lines.append(
                        f"   - {reason}"
                    )

        return "\n".join(lines)

    @staticmethod
    def _build_listing_details(
        recommendation: RecommendationScore,
    ) -> str:
        listing = recommendation.listing
        details = []

        if listing.bedrooms_total is not None:
            details.append(
                f"{listing.bedrooms_total} bed"
            )

        if listing.bathrooms_total_integer is not None:
            details.append(
                f"{listing.bathrooms_total_integer} bath"
            )

        if listing.city:
            details.append(
                listing.city
            )

        if listing.list_price is not None:
            details.append(
                f"${listing.list_price:,.0f}"
            )

        if listing.days_on_market is not None:
            details.append(
                f"{listing.days_on_market} days on market"
            )

        return " | ".join(details)

    @staticmethod
    def _build_search_match_reasons(
        intent: PropertyIntent,
        recommendation: RecommendationScore,
    ) -> list[str]:
        listing = recommendation.listing
        reasons = []

        if (
            intent.city
            and listing.city
            and listing.city.lower() == intent.city.lower()
        ):
            reasons.append(
                f"in {listing.city}"
            )

        if (
            intent.max_price is not None
            and listing.list_price is not None
            and listing.list_price <= intent.max_price
        ):
            reasons.append(
                f"within the ${intent.max_price:,.0f} budget"
            )

        if (
            intent.min_bedrooms is not None
            and listing.bedrooms_total is not None
            and listing.bedrooms_total >= intent.min_bedrooms
        ):
            reasons.append(
                f"at least {intent.min_bedrooms} bedrooms"
            )

        if (
            intent.min_bathrooms is not None
            and listing.bathrooms_total_integer is not None
            and listing.bathrooms_total_integer
            >= intent.min_bathrooms
        ):
            reasons.append(
                f"at least {intent.min_bathrooms:g} bathrooms"
            )

        if (
            intent.property_type
            and listing.property_sub_type
            and intent.property_type.lower()
            in listing.property_sub_type.lower()
        ):
            reasons.append(
                f"matches the {intent.property_type} property type"
            )

        if intent.keywords:
            reasons.append(
                "matches required keywords: "
                + ", ".join(intent.keywords)
            )

        return reasons