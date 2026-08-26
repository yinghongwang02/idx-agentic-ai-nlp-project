from src.orchestration.composition import (
    resolve_explicit_listing_id,
)


def test_resolve_explicit_listing_id():
    result = resolve_explicit_listing_id(
        (
            "Show me homes similar to "
            "listing TEST-001."
        )
    )

    assert result == "TEST-001"


def test_resolve_explicit_listing_id_with_id_label():
    result = resolve_explicit_listing_id(
        (
            "Find similar homes to "
            "listing id ABC_123."
        )
    )

    assert result == "ABC_123"


def test_resolve_listing_id_returns_none_for_implicit_reference():
    result = resolve_explicit_listing_id(
        "Show me more homes like this."
    )

    assert result is None