from pydantic import BaseModel, Field


class ListingSchema(BaseModel):
    listing_key: str = Field(..., description="Unique listing identifier from MLS/Trestle")
    listing_id: str | None = None

    unparsed_address: str
    city: str
    postal_code: str | None = None

    standard_status: str | None = None
    property_type: str | None = None
    property_sub_type: str | None = None

    list_price: float
    previous_list_price: float | None = None
    close_price: float | None = None
    close_date: str | None = None

    bedrooms_total: int | None = None
    bathrooms_total_integer: int | None = None
    living_area: float | None = None

    association_fee: float | None = None
    days_on_market: int | None = None

    latitude: float | None = None
    longitude: float | None = None

    public_remarks: str | None = None