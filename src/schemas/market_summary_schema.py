from pydantic import BaseModel


class MarketSummary(BaseModel):
    """
    Aggregated market metrics calculated from recent sold comparables.
    """

    city: str | None = None
    postal_code: str | None = None

    comp_count: int = 0

    median_close_price: float | None = None
    average_days_on_market: float | None = None
    average_sale_to_list_ratio: float | None = None
    average_price_per_sqft: float | None = None