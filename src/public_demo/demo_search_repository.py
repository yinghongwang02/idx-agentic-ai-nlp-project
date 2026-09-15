from __future__ import annotations

import csv
from pathlib import Path

from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema
from src.search.search_repository import SearchRepository


DEFAULT_DEMO_LISTINGS_PATH = Path(
    "data/public_demo/active_listings.csv"
)


class DemoSearchRepository(SearchRepository):
    """
    Public-demo repository backed by synthetic CSV data.

    This repository intentionally contains no connection to the
    private IDX MySQL database.
    """

    def __init__(
        self,
        data_path: Path = DEFAULT_DEMO_LISTINGS_PATH,
    ) -> None:
        self.data_path = data_path
        self.listings = self._load_listings()

    def _load_listings(self) -> list[ListingSchema]:
        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Demo listing data not found: {self.data_path}"
            )

        listings: list[ListingSchema] = []

        with self.data_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                listings.append(
                    ListingSchema(
                        listing_key=row["listing_key"],
                        listing_id=row["listing_id"],
                        unparsed_address=row["unparsed_address"],
                        city=row["city"],
                        postal_code=row["postal_code"],
                        property_sub_type=row["property_sub_type"],
                        list_price=float(row["list_price"]),
                        bedrooms_total=int(
                            row["bedrooms_total"]
                        ),
                        bathrooms_total_integer=int(
                            row["bathrooms_total_integer"]
                        ),
                        living_area=float(row["living_area"]),
                        association_fee=float(
                            row["association_fee"]
                        ),
                        days_on_market=int(
                            row["days_on_market"]
                        ),
                        public_remarks=row["public_remarks"],
                    )
                )

        return listings

    def search(
        self,
        intent: PropertyIntent,
        limit: int = 5,
    ) -> list[ListingSchema]:

        results = self.listings

        if intent.city:
            city = intent.city.strip().lower()
            results = [
                listing
                for listing in results
                if listing.city.lower() == city
            ]

        if intent.max_price is not None:
            results = [
                listing
                for listing in results
                if listing.list_price <= intent.max_price
            ]

        if intent.min_bedrooms is not None:
            results = [
                listing
                for listing in results
                if (
                    listing.bedrooms_total is not None
                    and listing.bedrooms_total
                    >= intent.min_bedrooms
                )
            ]

        if intent.min_bathrooms is not None:
            results = [
                listing
                for listing in results
                if (
                    listing.bathrooms_total_integer is not None
                    and listing.bathrooms_total_integer
                    >= intent.min_bathrooms
                )
            ]

        if intent.property_type:
            requested_type = (
                intent.property_type
                .replace(" ", "")
                .lower()
            )

            results = [
                listing
                for listing in results
                if (
                    listing.property_sub_type
                    and listing.property_sub_type
                    .replace(" ", "")
                    .lower()
                    == requested_type
                )
            ]

        return results[:limit]