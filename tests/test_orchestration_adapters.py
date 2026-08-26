from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from src.orchestration.adapters import (
    KnowledgeAdapter,
    MarketAdapter,
    PropertySearchAdapter,
    RecommendationAdapter,
)


# =====================================================================
# PropertySearchAdapter
# =====================================================================


def test_property_search_adapter_calls_workflow():
    class FakeWorkflow:
        def __init__(self) -> None:
            self.received_queries: list[str] = []

        def run(
            self,
            user_query: str,
        ) -> dict[str, Any]:
            self.received_queries.append(
                user_query
            )

            return {
                "final_response": (
                    "Found 2 homes in Irvine."
                ),
                "recommendations": [
                    "listing-1",
                    "listing-2",
                ],
                "blocked": False,
                "error": None,
            }

    workflow = FakeWorkflow()

    adapter = PropertySearchAdapter(
        workflow=workflow,
    )

    state = {
        "user_query": (
            "Find homes in Irvine."
        ),
        "session_id": "test-session",
    }

    result = adapter(state)

    assert workflow.received_queries == [
        "Find homes in Irvine."
    ]

    assert result == {
        "final_response": (
            "Found 2 homes in Irvine."
        ),
        "recommendations": [
            "listing-1",
            "listing-2",
        ],
        "blocked": False,
        "error": None,
    }


def test_property_search_adapter_normalizes_missing_fields():
    class FakeWorkflow:
        def run(
            self,
            user_query: str,
        ) -> dict[str, Any]:
            return {
                "final_response": "No results.",
            }

    adapter = PropertySearchAdapter(
        workflow=FakeWorkflow(),
    )

    result = adapter(
        {
            "user_query": (
                "Find homes in Pasadena."
            )
        }
    )

    assert result == {
        "final_response": "No results.",
        "recommendations": [],
        "blocked": False,
        "error": None,
    }


# =====================================================================
# MarketAdapter
# =====================================================================


def test_market_adapter_parses_city_and_calls_market_agent():
    class FakeIntentAgent:
        def __init__(self) -> None:
            self.received_queries: list[str] = []

        def run(
            self,
            query: str,
        ):
            self.received_queries.append(
                query
            )

            return SimpleNamespace(
                city="Pasadena",
            )

    class FakeMarketAgent:
        def __init__(self) -> None:
            self.received_calls: list[
                dict[str, Any]
            ] = []

        def run(
            self,
            *,
            city: str,
        ):
            self.received_calls.append(
                {
                    "city": city,
                }
            )

            return {
                "city": city,
                "trend": "rising",
            }

    intent_agent = FakeIntentAgent()
    market_agent = FakeMarketAgent()

    adapter = MarketAdapter(
        market_agent=market_agent,
        intent_agent=intent_agent,
    )

    state = {
        "user_query": (
            "Are Pasadena home prices rising?"
        )
    }

    result = adapter(state)

    assert intent_agent.received_queries == [
        "Are Pasadena home prices rising?"
    ]

    assert market_agent.received_calls == [
        {
            "city": "Pasadena",
        }
    ]

    assert result == {
        "city": "Pasadena",
        "trend": "rising",
    }


def test_market_adapter_requires_city():
    class FakeIntentAgent:
        def run(
            self,
            query: str,
        ):
            return SimpleNamespace(
                city=None,
            )

    class FakeMarketAgent:
        def run(
            self,
            *,
            city: str,
        ):
            raise AssertionError(
                "MarketAgent should not run "
                "without a city."
            )

    adapter = MarketAdapter(
        market_agent=FakeMarketAgent(),
        intent_agent=FakeIntentAgent(),
    )

    with pytest.raises(
        ValueError,
        match=(
            "Market analysis requires a city"
        ),
    ):
        adapter(
            {
                "user_query": (
                    "Are prices rising?"
                )
            }
        )


# =====================================================================
# RecommendationAdapter
# =====================================================================


def test_recommendation_adapter_resolves_listing_id():
    class FakeRecommendationService:
        def __init__(self) -> None:
            self.received_calls: list[
                dict[str, Any]
            ] = []

        def recommend(
            self,
            *,
            target_listing_id: str,
            top_k: int,
        ):
            self.received_calls.append(
                {
                    "target_listing_id": (
                        target_listing_id
                    ),
                    "top_k": top_k,
                }
            )

            return [
                {
                    "listing_id": "TEST-002",
                },
                {
                    "listing_id": "TEST-003",
                },
            ]

    resolver_calls: list[str] = []

    def fake_listing_id_resolver(
        query: str,
    ) -> str | None:
        resolver_calls.append(query)
        return "TEST-001"

    service = FakeRecommendationService()

    adapter = RecommendationAdapter(
        service=service,
        listing_id_resolver=(
            fake_listing_id_resolver
        ),
    )

    state = {
        "user_query": (
            "Show me homes similar "
            "to TEST-001."
        )
    }

    result = adapter(state)

    assert resolver_calls == [
        "Show me homes similar to TEST-001."
    ]

    assert service.received_calls == [
        {
            "target_listing_id": (
                "TEST-001"
            ),
            "top_k": 5,
        }
    ]

    assert result == [
        {
            "listing_id": "TEST-002",
        },
        {
            "listing_id": "TEST-003",
        },
    ]


def test_recommendation_adapter_requires_listing_id():
    class FakeRecommendationService:
        def recommend(
            self,
            *,
            target_listing_id: str,
            top_k: int,
        ):
            raise AssertionError(
                "Recommendation service "
                "should not run without "
                "a listing ID."
            )

    def missing_listing_id(
        query: str,
    ) -> None:
        return None

    adapter = RecommendationAdapter(
        service=FakeRecommendationService(),
        listing_id_resolver=(
            missing_listing_id
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "Similar-home recommendation "
            "requires a target listing ID"
        ),
    ):
        adapter(
            {
                "user_query": (
                    "Show me similar homes."
                )
            }
        )


# =====================================================================
# KnowledgeAdapter
# =====================================================================


def test_knowledge_adapter_calls_answer_callable():
    received_queries: list[str] = []

    def fake_answer(
        query: str,
    ):
        received_queries.append(
            query
        )

        return {
            "answer": (
                "DOM means Days on Market."
            ),
            "sources": [
                "real_estate_terminology.md",
            ],
        }

    adapter = KnowledgeAdapter(
        answer_callable=fake_answer,
    )

    state = {
        "user_query": (
            "What does DOM mean "
            "in real estate?"
        )
    }

    result = adapter(state)

    assert received_queries == [
        (
            "What does DOM mean "
            "in real estate?"
        )
    ]

    assert result == {
        "answer": (
            "DOM means Days on Market."
        ),
        "sources": [
            "real_estate_terminology.md",
        ],
    }