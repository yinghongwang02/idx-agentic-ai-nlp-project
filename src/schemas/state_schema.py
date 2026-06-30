from typing import TypedDict, Any

from src.schemas.intent_schema import PropertyIntent


class AgentState(TypedDict, total=False):
    user_query: str
    intent: PropertyIntent
    listings: list[dict[str, Any]]
    compliance_status: str
    recommendations: list[dict[str, Any]]
    final_answer: str