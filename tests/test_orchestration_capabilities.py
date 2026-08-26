import pytest

from src.orchestration.capabilities import (
    KnowledgeCapability,
    MarketCapability,
    RecommendCapability,
)


class FakeIntent:
    def __init__(
        self,
        city: str | None,
    ) -> None:
        self.city = city


class FakeIntentAgent:
    def __init__(
        self,
        city: str | None,
    ) -> None:
        self.city = city

    def run(
        self,
        query: str,
    ) -> FakeIntent:
        return FakeIntent(
            city=self.city
        )


class FakeMarketAgent:
    def __init__(self) -> None:
        self.called_city = None

    def run(
        self,
        city: str,
    ) -> dict:
        self.called_city = city

        return {
            "city": city,
            "direction": "warming",
        }


class FakeRecommendationService:
    def __init__(self) -> None:
        self.called_listing_id = None
        self.called_top_k = None

    def recommend(
        self,
        target_listing_id: str,
        top_k: int,
    ) -> list[dict]:
        self.called_listing_id = (
            target_listing_id
        )
        self.called_top_k = top_k

        return [
            {
                "listing_id": "SIM123",
            }
        ]


class FakeKnowledgeAnswerer:
    def __init__(self) -> None:
        self.called_question = None

    def answer(
        self,
        question: str,
    ) -> dict:
        self.called_question = question

        return {
            "answer": "DaysOnMarket is an MLS field.",
            "sources": [],
        }


def test_recommend_capability_extracts_listing_id() -> None:
    service = FakeRecommendationService()

    capability = RecommendCapability(
        service=service,
        top_k=5,
    )

    result = capability.run(
        "Find similar homes to listing ABC123."
    )

    assert service.called_listing_id == "ABC123"
    assert service.called_top_k == 5

    assert result == [
        {
            "listing_id": "SIM123",
        }
    ]


def test_recommend_capability_requires_listing_id() -> None:
    service = FakeRecommendationService()

    capability = RecommendCapability(
        service=service,
    )

    with pytest.raises(
        ValueError,
        match="target listing ID",
    ):
        capability.run(
            "Show me homes similar to this listing."
        )


def test_market_capability_extracts_city_and_calls_agent() -> None:
    market_agent = FakeMarketAgent()

    intent_agent = FakeIntentAgent(
        city="Pasadena"
    )

    capability = MarketCapability(
        market_agent=market_agent,
        intent_agent=intent_agent,
    )

    result = capability.run(
        "Is the Pasadena market warming?"
    )

    assert market_agent.called_city == "Pasadena"

    assert result == {
        "city": "Pasadena",
        "direction": "warming",
    }


def test_knowledge_capability_delegates_to_answerer() -> None:
    answerer = FakeKnowledgeAnswerer()

    capability = KnowledgeCapability(
        answerer=answerer
    )

    result = capability.run(
        "What does DaysOnMarket mean?"
    )

    assert (
        answerer.called_question
        == "What does DaysOnMarket mean?"
    )

    assert result["answer"] == (
        "DaysOnMarket is an MLS field."
    )