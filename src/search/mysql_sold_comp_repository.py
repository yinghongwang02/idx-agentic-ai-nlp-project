import os
from datetime import date

import mysql.connector
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

from src.schemas.sold_comp_schema import SoldCompSchema
from src.search.sold_comp_formatter import format_mysql_sold_comp
from src.search.sold_comp_repository import SoldCompRepository


load_dotenv()


class MySQLSoldCompRepository(SoldCompRepository):
    """
    MySQL-backed implementation of SoldCompRepository.

    Responsibility:
        - connect to MySQL
        - retrieve recent sold comparable properties
        - convert MySQL rows into SoldCompSchema
    """

    def __init__(self) -> None:
        self.config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "idx_exchange"),
            "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
        }

    def find_recent_comps(
        self,
        city: str,
        postal_code: str | None = None,
        months: int = 12,
        limit: int = 500,
    ) -> list[SoldCompSchema]:
        end_date = date.today()
        start_date = end_date - relativedelta(months=months)

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

        params = [
            city,
            start_date,
            end_date,
        ]

        if postal_code:
            sql_parts.append("AND PostalCode = %s")
            params.append(postal_code)

        sql_parts.append("ORDER BY CloseDate DESC")
        sql_parts.append("LIMIT %s")
        params.append(limit)

        sql = "\n".join(sql_parts)

        connection = mysql.connector.connect(**self.config)

        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            return [
                format_mysql_sold_comp(row)
                for row in rows
            ]

        finally:
            cursor.close()
            connection.close()