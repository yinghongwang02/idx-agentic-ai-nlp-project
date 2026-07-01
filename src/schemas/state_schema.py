from typing import TypedDict

from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema


class AgentState(TypedDict, total=False):
    user_query: str
    intent: PropertyIntent
    listings: list[ListingSchema]
    compliance_status: str
    recommendations: list[ListingSchema]
    final_answer: str