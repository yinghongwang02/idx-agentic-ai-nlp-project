from datetime import date

from pydantic import BaseModel


class SoldCompSchema(BaseModel):
    """
    Normalized schema for a sold comparable property.

    This schema contains only the fields needed for:
    - market analytics
    - comparable property analysis
    - negotiation scoring
    """

    listing_key: str

    city: str | None = None
    postal_code: str | None = None
    unparsed_address: str | None = None

    property_sub_type: str | None = None

    bedrooms_total: int | None = None
    bathrooms_total_integer: int | None = None
    living_area: float | None = None

    list_price: float | None = None
    original_list_price: float | None = None
    close_price: float | None = None
    close_date: date | None = None

    days_on_market: int | None = None
    association_fee: float | None = None