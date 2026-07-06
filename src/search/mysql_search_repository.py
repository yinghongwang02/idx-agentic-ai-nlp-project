import os

import mysql.connector
from dotenv import load_dotenv

from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema
from src.search.property_formatter import format_mysql_listing
from src.search.query_builder import PropertyQueryBuilder
from src.search.search_repository import SearchRepository

load_dotenv()


class MySQLSearchRepository(SearchRepository):
    """
    MySQL-backed implementation of SearchRepository.

    Responsibility:
        - connect to MySQL
        - execute parameterized SQL from QueryBuilder
        - convert MySQL rows into ListingSchema
    """

    def __init__(self) -> None:
        self.query_builder = PropertyQueryBuilder()
        self.config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "idx_exchange"),
            "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
        }

    def search(self, intent: PropertyIntent, limit: int = 5) -> list[ListingSchema]:
        sql, params = self.query_builder.build(
            intent=intent,
            limit=limit,
            offset=0,
        )

        connection = mysql.connector.connect(**self.config)

        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            return [format_mysql_listing(row) for row in rows]

        finally:
            cursor.close()
            connection.close()