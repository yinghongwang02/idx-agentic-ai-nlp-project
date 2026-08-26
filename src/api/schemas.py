from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


CapabilityRoute = Literal[
    "search",
    "market",
    "recommend",
    "knowledge",
]

PrimaryRoute = Literal[
    "search",
    "market",
    "recommend",
    "knowledge",
    "mixed",
]


# =====================================================================
# Shared validation
# =====================================================================


class QueryRequestBase(BaseModel):
    """
    Base request model for natural-language orchestrator queries.
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural-language user request.",
    )

    session_id: str | None = Field(
        default=None,
        max_length=200,
        description=(
            "Optional session identifier used for "
            "conversation-aware workflows."
        ),
    )

    @field_validator("query")
    @classmethod
    def validate_query(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "query must not be empty."
            )

        return value

    @field_validator("session_id")
    @classmethod
    def normalize_session_id(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        return value


# =====================================================================
# Request schemas
# =====================================================================


class SearchRequest(QueryRequestBase):
    """
    Request for property-search-oriented queries.
    """

    pass


class ChatRequest(QueryRequestBase):
    """
    General conversational request routed through the unified
    Week 9 orchestrator.
    """

    pass


class RecommendationRequest(BaseModel):
    """
    Request for listing-to-listing similar-home recommendation.

    Week 9 MVP requires an explicit MLS listing ID.
    """

    listing_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description=(
            "Explicit MLS listing ID used as the "
            "recommendation target."
        ),
    )

    session_id: str | None = Field(
        default=None,
        max_length=200,
        description="Optional session identifier.",
    )

    @field_validator("listing_id")
    @classmethod
    def validate_listing_id(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "listing_id must not be empty."
            )

        return value

    @field_validator("session_id")
    @classmethod
    def normalize_session_id(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        return value


# =====================================================================
# Response schemas
# =====================================================================


class HealthResponse(BaseModel):
    """
    Lightweight API-process health response.
    """

    status: Literal["ok"] = "ok"

    environment: str = Field(
        ...,
        description="Current application environment.",
    )


class OrchestrationResponse(BaseModel):
    """
    Stable public representation of an orchestrator result.

    Internal capability-specific objects remain inside the application
    state and are intentionally not exposed through the first API
    contract.
    """

    route: PrimaryRoute

    routes: list[CapabilityRoute] = Field(
        default_factory=list
    )

    route_reason: str = ""

    agents_invoked: list[str] = Field(
        default_factory=list
    )

    final_response: str

    errors: list[str] = Field(
        default_factory=list
    )

    session_id: str | None = None