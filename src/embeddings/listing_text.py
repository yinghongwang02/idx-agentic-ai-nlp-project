from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def clean_text(value: Any) -> str:
    """Convert a listing value into normalized single-line text."""
    if value is None:
        return ""

    text = str(value).strip()
    return " ".join(text.split())


def format_number(value: Any) -> str:
    """Format a numeric value without unnecessary decimal zeros."""
    if value is None or value == "":
        return ""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return clean_text(value)

    if number.is_integer():
        return str(int(number))

    return f"{number:.2f}".rstrip("0").rstrip(".")


def format_price(value: Any) -> str:
    """Format a listing price for embedding text."""
    if value is None or value == "":
        return ""

    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return clean_text(value)


def build_listing_embedding_text(listing: Mapping[str, Any]) -> str:
    """
    Build stable semantic text from one MLS listing.

    The text intentionally excludes listing identifiers because identifiers
    should be retained as metadata rather than embedded as semantic content.
    """
    parts: list[str] = []

    property_type = clean_text(listing.get("L_Type_"))
    city = clean_text(listing.get("L_City"))
    state = clean_text(listing.get("L_State"))
    postal_code = clean_text(listing.get("L_Zip"))
    bedrooms = format_number(listing.get("L_Keyword2"))
    bathrooms = format_number(listing.get("LM_Dec_3"))
    living_area = format_number(listing.get("LM_Int2_3"))
    price = format_price(listing.get("L_SystemPrice"))
    remarks = clean_text(listing.get("L_Remarks"))

    if property_type:
        parts.append(f"Property type: {property_type}.")

    location_parts = [
        value for value in (city, state, postal_code) if value
    ]
    if location_parts:
        parts.append(f"Location: {', '.join(location_parts)}.")

    feature_parts: list[str] = []

    if bedrooms:
        feature_parts.append(f"{bedrooms} bedrooms")

    if bathrooms:
        feature_parts.append(f"{bathrooms} bathrooms")

    if living_area:
        feature_parts.append(f"{living_area} square feet")

    if feature_parts:
        parts.append(f"Features: {', '.join(feature_parts)}.")

    if price:
        parts.append(f"List price: {price}.")

    if remarks:
        parts.append(f"Description: {remarks}")

    embedding_text = " ".join(parts).strip()

    if not embedding_text:
        raise ValueError(
            "Cannot build embedding text because the listing has no usable fields."
        )

    return embedding_text