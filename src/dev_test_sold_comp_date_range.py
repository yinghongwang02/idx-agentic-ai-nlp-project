from datetime import date

import mysql.connector

from src.search.mysql_sold_comp_repository import MySQLSoldCompRepository


def main() -> None:
    repository = MySQLSoldCompRepository()

    city = "Pasadena"
    start_date = date(2026, 5, 25)
    end_date = date(2026, 8, 25)
    limit = 500

    print("=" * 80)
    print("DATABASE CONNECTION DIAGNOSTIC")
    print("=" * 80)

    print("Host:    ", repository.config["host"])
    print("Port:    ", repository.config["port"])
    print("User:    ", repository.config["user"])
    print("Database:", repository.config["database"])
    print()

    connection = mysql.connector.connect(
        **repository.config
    )

    cursor = connection.cursor()

    # 1. Identify the actual server/database
    cursor.execute(
        """
        SELECT
            DATABASE(),
            @@hostname,
            @@port
        """
    )

    print(
        "Connected database/server:",
        cursor.fetchone(),
    )

    # 2. Count all Pasadena rows
    cursor.execute(
        """
        SELECT
            COUNT(*),
            MIN(CloseDate),
            MAX(CloseDate)
        FROM california_sold
        WHERE City = %s
        """,
        (city,),
    )

    print(
        "All Pasadena rows:",
        cursor.fetchone(),
    )

    # 3. Same exact query as repository
    cursor.execute(
        """
        SELECT
            COUNT(*),
            MIN(CloseDate),
            MAX(CloseDate)
        FROM california_sold
        WHERE City = %s
          AND CloseDate >= %s
          AND CloseDate <= %s
          AND ClosePrice IS NOT NULL
          AND ClosePrice > 0
        """,
        (
            city,
            start_date.isoformat(),
            end_date.isoformat(),
        ),
    )

    print(
        "Pasadena rows in test window:",
        cursor.fetchone(),
    )

    cursor.close()
    connection.close()

    print()
    print("=" * 80)
    print("REPOSITORY QUERY")
    print("=" * 80)

    comps = repository.find_comps_by_date_range(
        city=city,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )

    print("Repository rows:", len(comps))

    if comps:
        close_dates = [
            comp.close_date
            for comp in comps
            if comp.close_date is not None
        ]

        print("Repository min date:", min(close_dates))
        print("Repository max date:", max(close_dates))


if __name__ == "__main__":
    main()