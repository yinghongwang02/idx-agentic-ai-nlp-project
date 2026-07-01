from src.schemas.listing_schema import ListingSchema


class RecommendationAgent:
    def run(self, listings: list[ListingSchema]) -> list[ListingSchema]:
        ranked = sorted(
            listings,
            key=lambda listing: (
                listing.days_on_market if listing.days_on_market is not None else 999,
                listing.list_price,
            ),
        )

        return ranked[:5]