from src.schemas.listing_schema import ListingSchema


class ExplanationAgent:
    def run(self, recommendations: list[ListingSchema]) -> str:
        if not recommendations:
            return "No matching listings found."

        lines = ["Top matching listings:"]

        for listing in recommendations:
            lines.append(
                f"- {listing.listing_key}: "
                f"{listing.bedrooms_total} bed / "
                f"{listing.bathrooms_total_integer} bath in "
                f"{listing.city} for ${listing.list_price:,.0f}. "
                f"Days on market: {listing.days_on_market}. "
                f"Address: {listing.unparsed_address}."
            )

        return "\n".join(lines)