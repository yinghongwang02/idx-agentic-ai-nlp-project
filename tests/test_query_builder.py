from src.search.query_builder import PropertyQueryBuilder
from src.schemas.intent_schema import PropertyIntent


def test_query_builder_city_price_bedrooms():
    intent = PropertyIntent(
        city="Irvine",
        max_price=900000,
        min_bedrooms=3,
        property_type="condo",
        keywords=[],
    )

    builder = PropertyQueryBuilder()
    sql, params = builder.build(intent, limit=5, offset=0)

    assert "L_City = %s" in sql
    assert "L_SystemPrice <= %s" in sql
    assert "L_Keyword2 >= %s" in sql
    assert "L_Type_ LIKE %s" in sql
    assert "LIMIT %s OFFSET %s" in sql

    assert params == ["Irvine", 900000, 3, "%condo%", 5, 0]