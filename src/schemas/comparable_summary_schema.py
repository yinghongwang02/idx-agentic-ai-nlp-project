from pydantic import BaseModel


class ComparableSummary(BaseModel):
    """
    Aggregated metrics calculated from matched sold comparables.
    """

    match_level: str
    comp_count: int

    median_close_price: float | None = None
    average_days_on_market: float | None = None
    average_sale_to_list_ratio: float | None = None
    median_price_per_sqft: float | None = None