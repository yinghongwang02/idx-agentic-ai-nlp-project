from pydantic import BaseModel


class ListingSchema(BaseModel):
    listing_id: str
    address: str
    city: str
    zip_code: str
    property_type: str
    list_price: float
    bedrooms: int
    bathrooms: float
    living_area: float | None = None
    association_fee: float | None = None
    days_on_market: int | None = None
    remarks: str | None = None