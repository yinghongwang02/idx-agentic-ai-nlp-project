from pydantic import BaseModel

from src.schemas.comparable_summary_schema import ComparableSummary
from src.schemas.market_summary_schema import MarketSummary


class MarketContext(BaseModel):
    """
    Combined market context for one active listing.
    """

    city_market: MarketSummary
    comparable_market: ComparableSummary