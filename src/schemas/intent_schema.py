from pydantic import BaseModel


class PropertyIntent(BaseModel):
    city: str | None = None
    max_price: float | None = None
    min_bedrooms: int | None = None
    min_bathrooms: float | None = None
    property_type: str | None = None
    keywords: list[str] = []