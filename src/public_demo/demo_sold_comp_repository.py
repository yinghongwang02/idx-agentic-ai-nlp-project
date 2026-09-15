from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from dateutil.relativedelta import relativedelta

from src.schemas.comparable_result_schema import ComparableResult
from src.schemas.listing_schema import ListingSchema
from src.schemas.sold_comp_schema import SoldCompSchema
from src.search.sold_comp_repository import SoldCompRepository


DEFAULT_DEMO_SOLD_PATH = Path(
    "data/public_demo/sold_comps.csv"
)


class DemoSoldCompRepository(SoldCompRepository):
    """
    Public-demo sold comparable repository backed by
    deterministic synthetic CSV data.
    """

    def __init__(
        self,
        data_path: Path = DEFAULT_DEMO_SOLD_PATH,
    ) -> None:
        self.data_path = data_path
        self.comps = self._load_comps()

    def _load_comps(self) -> list[SoldCompSchema]:
        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Demo sold-comp data not found: {self.data_path}"
            )

        comps: list[SoldCompSchema] = []

        with self.data_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                comps.append(
                    SoldCompSchema(
                        listing_key=row["listing_key"],
                        city=row["city"],
                        postal_code=row["postal_code"],
                        unparsed_address=row["unparsed_address"],
                        property_sub_type=row[
                            "property_sub_type"
                        ],
                        bedrooms_total=int(
                            row["bedrooms_total"]
                        ),
                        bathrooms_total_integer=int(
                            row["bathrooms_total_integer"]
                        ),
                        living_area=float(row["living_area"]),
                        list_price=float(row["list_price"]),
                        original_list_price=float(
                            row["original_list_price"]
                        ),
                        close_price=float(row["close_price"]),
                        close_date=date.fromisoformat(
                            row["close_date"]
                        ),
                        days_on_market=int(
                            row["days_on_market"]
                        ),
                        association_fee=float(
                            row["association_fee"]
                        ),
                    )
                )

        return sorted(
            comps,
            key=lambda comp: comp.close_date or date.min,
            reverse=True,
        )

    def find_recent_comps(
        self,
        city: str,
        postal_code: str | None = None,
        months: int = 12,
        limit: int = 500,
    ) -> list[SoldCompSchema]:

        city_comps = [
            comp
            for comp in self.comps
            if comp.city
            and comp.city.lower() == city.lower()
            and (
                postal_code is None
                or comp.postal_code == postal_code
            )
        ]

        if not city_comps:
            return []

        anchor_date = city_comps[0].close_date

        if anchor_date is None:
            return []

        start_date = anchor_date - relativedelta(
            months=months
        )

        return [
            comp
            for comp in city_comps
            if comp.close_date is not None
            and start_date <= comp.close_date <= anchor_date
        ][:limit]

    def find_comps_by_date_range(
        self,
        city: str,
        start_date: date,
        end_date: date,
        postal_code: str | None = None,
        limit: int = 500,
    ) -> list[SoldCompSchema]:

        results = [
            comp
            for comp in self.comps
            if comp.city
            and comp.city.lower() == city.lower()
            and comp.close_date is not None
            and start_date <= comp.close_date <= end_date
            and (
                postal_code is None
                or comp.postal_code == postal_code
            )
        ]

        return results[:limit]

    def find_similar_comps(
        self,
        listing: ListingSchema,
        months: int = 12,
        limit: int = 100,
        minimum_comps: int = 5,
    ) -> ComparableResult:

        recent = self.find_recent_comps(
            city=listing.city,
            months=months,
            limit=500,
        )

        strict = [
            comp
            for comp in recent
            if self._matches(
                comp,
                listing,
                require_zip=True,
                sqft_tolerance=0.20,
            )
        ]

        if len(strict) >= minimum_comps:
            selected = strict[:limit]
            return ComparableResult(
                comps=selected,
                match_level="strict",
                comp_count=len(selected),
            )

        relaxed = [
            comp
            for comp in recent
            if self._matches(
                comp,
                listing,
                require_zip=False,
                sqft_tolerance=0.25,
            )
        ]

        if len(relaxed) >= minimum_comps:
            selected = relaxed[:limit]
            return ComparableResult(
                comps=selected,
                match_level="relaxed",
                comp_count=len(selected),
            )

        broad = [
            comp
            for comp in recent
            if (
                listing.property_sub_type is None
                or comp.property_sub_type
                == listing.property_sub_type
            )
        ]

        if len(broad) >= minimum_comps:
            selected = broad[:limit]
            return ComparableResult(
                comps=selected,
                match_level="broad",
                comp_count=len(selected),
            )

        selected = recent[:limit]

        return ComparableResult(
            comps=selected,
            match_level="market_fallback",
            comp_count=len(selected),
        )

    @staticmethod
    def _matches(
        comp: SoldCompSchema,
        listing: ListingSchema,
        require_zip: bool,
        sqft_tolerance: float,
    ) -> bool:

        if (
            require_zip
            and listing.postal_code
            and comp.postal_code != listing.postal_code
        ):
            return False

        if (
            listing.property_sub_type
            and comp.property_sub_type
            != listing.property_sub_type
        ):
            return False

        if (
            listing.bedrooms_total is not None
            and comp.bedrooms_total is not None
            and abs(
                comp.bedrooms_total
                - listing.bedrooms_total
            )
            > 1
        ):
            return False

        if (
            listing.bathrooms_total_integer is not None
            and comp.bathrooms_total_integer is not None
            and abs(
                comp.bathrooms_total_integer
                - listing.bathrooms_total_integer
            )
            > 1
        ):
            return False

        if (
            listing.living_area
            and comp.living_area
        ):
            lower = (
                listing.living_area
                * (1 - sqft_tolerance)
            )
            upper = (
                listing.living_area
                * (1 + sqft_tolerance)
            )

            if not lower <= comp.living_area <= upper:
                return False

        return True