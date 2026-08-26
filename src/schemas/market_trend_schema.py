from datetime import date
from typing import Literal

from pydantic import BaseModel


class MarketTrend(BaseModel):
    """
    Compare the latest three months of sold-market activity
    with the preceding three-month period.
    """

    anchor_date: date | None = None

    recent_start_date: date | None = None
    recent_end_date: date | None = None

    previous_start_date: date | None = None
    previous_end_date: date | None = None

    recent_comp_count: int = 0
    previous_comp_count: int = 0

    recent_median_close_price: float | None = None
    previous_median_close_price: float | None = None
    median_price_change_pct: float | None = None

    recent_median_price_per_sqft: float | None = None
    previous_median_price_per_sqft: float | None = None
    median_ppsf_change_pct: float | None = None

    recent_average_days_on_market: float | None = None
    previous_average_days_on_market: float | None = None
    average_dom_change: float | None = None

    recent_average_sale_to_list_ratio: float | None = None
    previous_average_sale_to_list_ratio: float | None = None
    sale_to_list_change: float | None = None

    direction: Literal[
        "warming",
        "stable",
        "cooling",
        "insufficient_data",
    ] = "insufficient_data"