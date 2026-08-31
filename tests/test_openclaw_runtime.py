from __future__ import annotations

import pytest

from src.openclaw_runtime.runtime import (
    OpenClawRuntime,
    RuntimeRequest,
)
from src.openclaw_runtime.skill_adapter import (
    RealEstateCopilotSkill,
)
from src.orchestration.orchestrator import (
    Orchestrator,
)
from src.orchestration.router import (
    IntentRouter,
)


# =====================================================================
# Lightweight capability doubles
# =====================================================================


def fake_search_handler(state):
    return {
        "final_response": (
            "Found 3 homes matching the search criteria."
        ),
        "recommendations": [
            "listing-1",
            "listing-2",
            "listing-3",
        ],
        "blocked": False,
        "error": None,
    }


def fake_market_handler(state):
    return {
        "city": "Irvine",
        "summary": (
            "The Irvine market is currently stable."
        ),
    }


def fake_recommendation_handler(state):
    return [
        {
            "listing_id": "similar-1",
            "hybrid_similarity_score": 91.5,
        }
    ]


def fake_knowledge_handler(state):
    return {
        "answer": (
            "DOM means Days on Market."
        ),
        "sources": [
            "mls_field_mapping.md",
        ],
    }


# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture
def orchestrator():
    router = IntentRouter()

    return Orchestrator(
        router=router.route,
        search_handler=fake_search_handler,
        market_handler=fake_market_handler,
        recommendation_handler=(
            fake_recommendation_handler
        ),
        knowledge_handler=(
            fake_knowledge_handler
        ),
    )


@pytest.fixture
def skill(orchestrator):
    return RealEstateCopilotSkill(
        orchestrator=orchestrator,
    )


@pytest.fixture
def runtime(skill):
    return OpenClawRuntime(
        skill=skill,
    )


# =====================================================================
# Runtime boundary
# =====================================================================


def test_runtime_preserves_session_and_channel(
    runtime,
):
    response = runtime.handle(
        RuntimeRequest(
            message=(
                "Find homes in Irvine under $1.5M"
            ),
            session_id="buyer-123",
            channel="whatsapp",
        )
    )

    assert response.session_id == "buyer-123"
    assert response.channel == "whatsapp"

    assert (
        response.raw_state["session_id"]
        == "buyer-123"
    )


# =====================================================================
# Search route
# =====================================================================


def test_runtime_executes_search_route(
    runtime,
):
    response = runtime.handle_message(
        "Find homes in Irvine under $1.5M",
        session_id="search-session",
    )

    assert response.route == "search"
    assert response.routes == ("search",)

    assert set(
        response.agents_invoked
    ) == {"search"}

    assert (
        "Found 3 homes"
        in response.text
    )

    assert (
        response.raw_state[
            "search_result"
        ]["blocked"]
        is False
    )


# =====================================================================
# Knowledge route
# =====================================================================


def test_runtime_executes_knowledge_route(
    runtime,
):
    response = runtime.handle_message(
        "What does DOM mean in real estate?",
        session_id="knowledge-session",
    )

    assert response.route == "knowledge"
    assert response.routes == (
        "knowledge",
    )

    assert set(
        response.agents_invoked
    ) == {"knowledge"}

    assert response.text == (
        "DOM means Days on Market."
    )

    assert (
        response.raw_state[
            "knowledge_result"
        ]["sources"]
        == ["mls_field_mapping.md"]
    )


# =====================================================================
# Mixed route
# =====================================================================


def test_runtime_executes_mixed_search_market_route(
    runtime,
):
    response = runtime.handle_message(
        (
            "Find homes in Irvine under $1.5M "
            "and tell me about the local market."
        ),
        session_id="mixed-session",
    )

    assert response.route == "mixed"

    assert set(response.routes) == {
        "search",
        "market",
    }

    assert set(
        response.agents_invoked
    ) == {
        "search",
        "market",
    }

    assert (
        "Property Search:"
        in response.text
    )

    assert (
        "Market Analysis:"
        in response.text
    )

    assert (
        "Found 3 homes"
        in response.text
    )

    assert (
        "Irvine"
        in response.text
    )


# =====================================================================
# Structured state preservation
# =====================================================================


def test_runtime_preserves_structured_orchestrator_state(
    runtime,
):
    response = runtime.handle_message(
        (
            "Find homes in Irvine and "
            "tell me about the market"
        )
    )

    state = response.raw_state

    assert "search_result" in state
    assert "market_result" in state
    assert "final_response" in state

    assert state["route"] == "mixed"

    assert set(
        state["agents_invoked"]
    ) == {
        "search",
        "market",
    }


# =====================================================================
# Input validation
# =====================================================================


def test_runtime_rejects_empty_message(
    runtime,
):
    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        runtime.handle_message(
            "   "
        )