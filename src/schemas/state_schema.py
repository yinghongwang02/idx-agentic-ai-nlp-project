from typing import Any, TypedDict

from src.schemas.compliance_schema import ComplianceReport
from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema


class AgentState(TypedDict, total=False):
    user_query: str
    intent: PropertyIntent
    listings: list[ListingSchema]
    compliance_status: str
    recommendations: list[ListingSchema]
    final_answer: str

    # Compliance result for the incoming query
    query_compliance: ComplianceReport
    # Snapshot of current session preferences
    memory_snapshot: dict[str, Any]
    # Compliance result for generated output
    output_compliance: ComplianceReport
    # Workflow control and diagnostics
    blocked: bool
    error: str | None

    search_results: list[ListingSchema]
    explanation: str
    final_response: str