from __future__ import annotations

import pytest

from src.communication.email_draft_agent import (
    EmailDraftAgent,
)
from src.orchestration.composition import (
    create_orchestrator,
)


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def real_orchestrator():
    return create_orchestrator()


@pytest.fixture
def email_agent():
    return EmailDraftAgent()


def test_real_market_result_builds_weekly_email_draft(
    real_orchestrator,
    email_agent,
):
    state = real_orchestrator.invoke(
        "Tell me about the Irvine real estate market."
    )

    assert state["route"] == "market"
    assert state.get("market_result") is not None
    assert not state.get("errors")

    market_summary = state["market_result"]

    draft = email_agent.draft_weekly_market_report(
        to="buyer@example.com",
        market_summary=market_summary,
    )

    assert draft.status == "pending_approval"
    assert draft.to == "buyer@example.com"

    assert "Weekly Real Estate Market Report" in (
        draft.subject
    )

    assert "Irvine" in draft.subject
    assert "Market Summary" in draft.body

    assert draft.metadata["draft_type"] == (
        "weekly_market_report"
    )

    assert draft.metadata["city"] == "Irvine"


def test_real_search_result_builds_property_digest(
    real_orchestrator,
    email_agent,
):
    state = real_orchestrator.invoke(
        "Find homes in Irvine under $1.5M"
    )

    assert state["route"] == "search"
    assert state.get("search_result") is not None
    assert not state.get("errors")

    search_result = state["search_result"]

    recommendations = search_result.get(
        "recommendations",
        [],
    )

    assert recommendations

    draft = email_agent.draft_property_digest(
        to="buyer@example.com",
        listings=recommendations,
        buyer_preferences=(
            "Homes in Irvine under $1.5M"
        ),
    )

    assert draft.status == "pending_approval"
    assert draft.to == "buyer@example.com"

    assert "Property Recommendations" in (
        draft.subject
    )

    assert "Irvine" in draft.body

    assert draft.metadata["draft_type"] == (
        "property_recommendation_digest"
    )

    assert (
        1
        <= draft.metadata["listing_count"]
        <= 5
    )