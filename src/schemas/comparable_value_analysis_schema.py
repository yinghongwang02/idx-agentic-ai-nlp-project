from pydantic import BaseModel


class ComparableValueAnalysis(BaseModel):
    """
    Comparable-based value analysis for one active listing.

    Raw value measures how attractive the asking price is relative
    to similar sold properties.

    Comparable quality measures how reliable the comparable evidence is.

    Adjusted value moves the raw value score toward neutral when
    comparable evidence is weaker.
    """

    raw_value_score: float
    comparable_quality_score: float
    adjusted_value_score: float

    asking_price_per_sqft: float | None = None
    comparable_median_price_per_sqft: float | None = None
    price_per_sqft_ratio: float | None = None

    match_level: str
    comp_count: int
    valid_ppsf_count: int
    ppsf_coverage_ratio: float

    signals: list[str]