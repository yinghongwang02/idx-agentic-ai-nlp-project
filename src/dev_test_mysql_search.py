from src.schemas.intent_schema import PropertyIntent
from src.search.mysql_search_repository import MySQLSearchRepository


def main() -> None:
    intent = PropertyIntent(
        city="Irvine",
        max_price=900000,
        min_bedrooms=3,
        min_bathrooms=2,
        property_type="Condominium",
        keywords=["pool"],
    )

    repository = MySQLSearchRepository()
    results = repository.search(intent=intent, limit=5)

    for item in results:
        print(item)


if __name__ == "__main__":
    main()