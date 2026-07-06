from src.schemas.intent_schema import PropertyIntent
from src.search.query_builder import PropertyQueryBuilder


def main() -> None:
    intent = PropertyIntent(
        city="Irvine",
        max_price=900000,
        min_bedrooms=3,
        min_bathrooms=2,
        property_type="Condominium",
        keywords=["pool", "view"],
    )

    builder = PropertyQueryBuilder()
    sql, params = builder.build(intent=intent, limit=5, offset=0)

    print("SQL:")
    print(sql)
    print()
    print("PARAMS:")
    print(params)


if __name__ == "__main__":
    main()