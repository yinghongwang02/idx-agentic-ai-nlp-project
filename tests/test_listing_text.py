import pytest

from src.embeddings.listing_text import build_listing_embedding_text


def test_build_listing_embedding_text_with_complete_listing() -> None:
    listing = {
        "L_ListingID": "12345",
        "L_Type_": "SingleFamilyResidence",
        "L_City": "Irvine",
        "L_State": "CA",
        "L_Zip": "92620",
        "L_SystemPrice": 1250000,
        "L_Keyword2": 3,
        "LM_Dec_3": 2,
        "LM_Int2_3": 1840,
        "L_Remarks": (
            "Remodeled home with a pool and mountain views."
        ),
    }

    result = build_listing_embedding_text(listing)

    assert "Property type: SingleFamilyResidence." in result
    assert "Location: Irvine, CA, 92620." in result
    assert "3 bedrooms" in result
    assert "2 bathrooms" in result
    assert "1840 square feet" in result
    assert "List price: $1,250,000." in result
    assert "pool and mountain views" in result
    assert "12345" not in result


def test_build_listing_embedding_text_handles_missing_values() -> None:
    listing = {
        "L_Type_": "Condominium",
        "L_City": "Irvine",
        "L_State": "CA",
        "L_Zip": None,
        "L_SystemPrice": None,
        "L_Keyword2": 2,
        "LM_Dec_3": None,
        "LM_Int2_3": None,
        "L_Remarks": "Bright end-unit condo.",
    }

    result = build_listing_embedding_text(listing)

    assert "Property type: Condominium." in result
    assert "Location: Irvine, CA." in result
    assert "2 bedrooms" in result
    assert "Bright end-unit condo." in result
    assert "None" not in result


def test_build_listing_embedding_text_without_remarks() -> None:
    listing = {
        "L_Type_": "Townhouse",
        "L_City": "Irvine",
        "L_Keyword2": 3,
        "LM_Dec_3": 2.5,
    }

    result = build_listing_embedding_text(listing)

    assert "Property type: Townhouse." in result
    assert "Location: Irvine." in result
    assert "3 bedrooms" in result
    assert "2.5 bathrooms" in result


def test_build_listing_embedding_text_normalizes_whitespace() -> None:
    listing = {
        "L_City": "  Irvine  ",
        "L_Remarks": "Open   floor\nplan with     natural light.",
    }

    result = build_listing_embedding_text(listing)

    assert "Location: Irvine." in result
    assert "Open floor plan with natural light." in result


def test_build_listing_embedding_text_rejects_empty_listing() -> None:
    listing = {
        "L_Type_": None,
        "L_City": None,
        "L_Remarks": "   ",
    }

    with pytest.raises(
        ValueError,
        match="no usable fields",
    ):
        build_listing_embedding_text(listing)