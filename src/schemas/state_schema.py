from typing import Any, TypedDict

from src.schemas.compliance_schema import ComplianceReport
from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema


class AgentState(TypedDict, total=False):
    # Current user input
    user_query: str

    # Parsed and memory-enriched intent
    intent: PropertyIntent

    # Session memory snapshot
    memory_snapshot: dict[str, Any]

    # Compliance
    query_compliance: ComplianceReport
    output_compliance: ComplianceReport

    # Search pipeline
    search_results: list[ListingSchema]
    recommendations: list[ListingSchema]

    # Generated text
    explanation: str
    final_response: str

    # Workflow control
    blocked: bool
    error: str | None