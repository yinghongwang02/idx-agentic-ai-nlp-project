from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema


class ExplanationAgent:
    def run(
        self,
        intent: PropertyIntent,
        recommendations: list[ListingSchema],
    ) -> str:
        if not recommendations:
            return "No matching listings found."

        lines = ["Top matching listings:"]

        for listing in recommendations:
            reasons = self._build_match_reasons(intent, listing)

            lines.append(
                f"- {listing.listing_key}: "
                f"{listing.bedrooms_total} bed / "
                f"{listing.bathrooms_total_integer} bath in "
                f"{listing.city} for ${listing.list_price:,.0f}. "
                f"Days on market: {listing.days_on_market}. "
                f"Address: {listing.unparsed_address}. "
                f"Matched because: {', '.join(reasons)}."
            )

        return "\n".join(lines)

    def _build_match_reasons(
        self,
        intent: PropertyIntent,
        listing: ListingSchema,
    ) -> list[str]:
        reasons = []

        if intent.city and listing.city.lower() == intent.city.lower():
            reasons.append(f"it is in {listing.city}")

        if intent.max_price and listing.list_price <= intent.max_price:
            reasons.append(f"it is under ${intent.max_price:,.0f}")

        if intent.min_bedrooms and listing.bedrooms_total:
            if listing.bedrooms_total >= intent.min_bedrooms:
                reasons.append(f"it has at least {intent.min_bedrooms} bedrooms")

        if intent.min_bathrooms and listing.bathrooms_total_integer:
            if listing.bathrooms_total_integer >= intent.min_bathrooms:
                reasons.append(f"it has at least {intent.min_bathrooms:g} bathrooms")

        if intent.property_type and listing.property_sub_type:
            if intent.property_type.lower() in listing.property_sub_type.lower():
                reasons.append(f"it matches the {intent.property_type} property type")

        if intent.keywords and listing.public_remarks:
            remarks = listing.public_remarks.lower()
            matched_keywords = [
                keyword for keyword in intent.keywords
                if keyword.lower() in remarks
            ]

            if matched_keywords:
                reasons.append(
                    "remarks mention " + ", ".join(matched_keywords)
                )

        if not reasons:
            reasons.append("it matched the available search filters")

        return reasons