import os
from datetime import date
from typing import Any

import mysql.connector
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

from src.schemas.comparable_result_schema import ComparableResult
from src.schemas.listing_schema import ListingSchema
from src.schemas.sold_comp_schema import SoldCompSchema
from src.search.sold_comp_formatter import format_mysql_sold_comp
from src.search.sold_comp_repository import SoldCompRepository


load_dotenv()


class MySQLSoldCompRepository(SoldCompRepository):

    def __init__(self) -> None:
        self.config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv(
                "MYSQL_DATABASE",
                "idx_exchange",
            ),
            "charset": os.getenv(
                "MYSQL_CHARSET",
                "utf8mb4",
            ),
        }

    def find_recent_comps(
        self,
        city: str,
        postal_code: str | None = None,
        months: int = 12,
        limit: int = 500,
    ) -> list[SoldCompSchema]:
        end_date = date.today()
        start_date = end_date - relativedelta(
            months=months
        )

        sql_parts = [
            """
            SELECT
                ListingKey,
                City,
                PostalCode,
                UnparsedAddress,
                PropertySubType,
                BedroomsTotal,
                BathroomsTotalInteger,
                LivingArea,
                ListPrice,
                OriginalListPrice,
                ClosePrice,
                CloseDate,
                DaysOnMarket,
                AssociationFee
            FROM california_sold
            WHERE City = %s
              AND CloseDate >= %s
              AND CloseDate <= %s
              AND ClosePrice IS NOT NULL
              AND ClosePrice > 0
            """
        ]

        params: list[Any] = [
            city,
            start_date,
            end_date,
        ]

        if postal_code:
            sql_parts.append(
                "AND PostalCode = %s"
            )
            params.append(postal_code)

        sql_parts.append(
            "ORDER BY CloseDate DESC"
        )
        sql_parts.append(
            "LIMIT %s"
        )
        params.append(limit)

        return self._execute_query(
            sql="\n".join(sql_parts),
            params=params,
        )

    def find_similar_comps(
        self,
        listing: ListingSchema,
        months: int = 12,
        limit: int = 100,
        minimum_comps: int = 5,
    ) -> ComparableResult:
        """
        Find comparable sold properties using four
        progressive matching levels.
        """

        strict_comps = self._query_comps(
            listing=listing,
            months=months,
            limit=limit,
            use_zip=True,
            use_property_type=True,
            use_bedrooms=True,
            use_bathrooms=True,
            sqft_tolerance=0.20,
        )

        if len(strict_comps) >= minimum_comps:
            return ComparableResult(
                comps=strict_comps,
                match_level="strict",
                comp_count=len(strict_comps),
            )

        relaxed_comps = self._query_comps(
            listing=listing,
            months=months,
            limit=limit,
            use_zip=False,
            use_property_type=True,
            use_bedrooms=True,
            use_bathrooms=True,
            sqft_tolerance=0.25,
        )

        if len(relaxed_comps) >= minimum_comps:
            return ComparableResult(
                comps=relaxed_comps,
                match_level="relaxed",
                comp_count=len(relaxed_comps),
            )

        broad_comps = self._query_comps(
            listing=listing,
            months=months,
            limit=limit,
            use_zip=False,
            use_property_type=True,
            use_bedrooms=False,
            use_bathrooms=False,
            sqft_tolerance=None,
        )

        if len(broad_comps) >= minimum_comps:
            return ComparableResult(
                comps=broad_comps,
                match_level="broad",
                comp_count=len(broad_comps),
            )

        market_comps = self.find_recent_comps(
            city=listing.city,
            months=months,
            limit=limit,
        )

        return ComparableResult(
            comps=market_comps,
            match_level="market_fallback",
            comp_count=len(market_comps),
        )

    def _query_comps(
        self,
        listing: ListingSchema,
        months: int,
        limit: int,
        use_zip: bool,
        use_property_type: bool,
        use_bedrooms: bool,
        use_bathrooms: bool,
        sqft_tolerance: float | None,
    ) -> list[SoldCompSchema]:
        end_date = date.today()
        start_date = end_date - relativedelta(
            months=months
        )

        sql_parts = [
            """
            SELECT
                ListingKey,
                City,
                PostalCode,
                UnparsedAddress,
                PropertySubType,
                BedroomsTotal,
                BathroomsTotalInteger,
                LivingArea,
                ListPrice,
                OriginalListPrice,
                ClosePrice,
                CloseDate,
                DaysOnMarket,
                AssociationFee
            FROM california_sold
            WHERE CloseDate >= %s
              AND CloseDate <= %s
              AND ClosePrice IS NOT NULL
              AND ClosePrice > 0
            """
        ]

        params: list[Any] = [
            start_date,
            end_date,
        ]

        if listing.city:
            sql_parts.append(
                "AND City = %s"
            )
            params.append(
                listing.city
            )

        if (
            use_zip
            and listing.postal_code
        ):
            sql_parts.append(
                "AND PostalCode = %s"
            )
            params.append(
                str(listing.postal_code)
            )

        if (
            use_property_type
            and listing.property_sub_type
        ):
            sql_parts.append(
                "AND PropertySubType = %s"
            )
            params.append(
                listing.property_sub_type
            )

        if (
            use_bedrooms
            and listing.bedrooms_total is not None
        ):
            sql_parts.append(
                """
                AND BedroomsTotal
                BETWEEN %s AND %s
                """
            )

            params.extend(
                [
                    max(
                        0,
                        listing.bedrooms_total - 1,
                    ),
                    listing.bedrooms_total + 1,
                ]
            )

        if (
            use_bathrooms
            and listing.bathrooms_total_integer
            is not None
        ):
            sql_parts.append(
                """
                AND BathroomsTotalInteger
                BETWEEN %s AND %s
                """
            )

            params.extend(
                [
                    max(
                        0,
                        listing
                        .bathrooms_total_integer
                        - 1,
                    ),
                    listing
                    .bathrooms_total_integer
                    + 1,
                ]
            )

        if (
            sqft_tolerance is not None
            and listing.living_area is not None
            and listing.living_area > 0
        ):
            minimum_sqft = (
                listing.living_area
                * (1 - sqft_tolerance)
            )

            maximum_sqft = (
                listing.living_area
                * (1 + sqft_tolerance)
            )

            sql_parts.append(
                """
                AND LivingArea
                BETWEEN %s AND %s
                """
            )

            params.extend(
                [
                    minimum_sqft,
                    maximum_sqft,
                ]
            )

        sql_parts.append(
            "ORDER BY CloseDate DESC"
        )

        sql_parts.append(
            "LIMIT %s"
        )

        params.append(limit)

        return self._execute_query(
            sql="\n".join(sql_parts),
            params=params,
        )

    def _execute_query(
        self,
        sql: str,
        params: list[Any],
    ) -> list[SoldCompSchema]:
        connection = mysql.connector.connect(
            **self.config
        )

        cursor = None

        try:
            cursor = connection.cursor(
                dictionary=True
            )

            cursor.execute(
                sql,
                params,
            )

            rows = cursor.fetchall()

            return [
                format_mysql_sold_comp(row)
                for row in rows
            ]

        finally:
            if cursor is not None:
                cursor.close()

            connection.close()