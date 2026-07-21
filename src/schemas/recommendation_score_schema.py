from pydantic import BaseModel

from src.schemas.listing_schema import ListingSchema


class RecommendationScore(BaseModel):
    """
    Structured recommendation score for one active listing.
    """

    listing: ListingSchema

    overall_score: float

    preference_match_score: float
    comparable_value_score: float
    negotiation_score: float

    recommendation_label: str
    reasons: list[str]