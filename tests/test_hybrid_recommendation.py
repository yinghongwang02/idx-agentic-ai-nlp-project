from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.recommendation.hybrid_recommendation import (
    HybridRecommendationService,
)
from src.schemas.listing_schema import ListingSchema


def make_listing(
    listing_key: str,
) -> ListingSchema:
    return ListingSchema(
        listing_key=listing_key,
        listing_id=listing_key,
        unparsed_address=(
            f"{listing_key} Test Street"
        ),
        city="Irvine",
        postal_code="92618",
        property_sub_type=(
            "SingleFamilyResidence"
        ),
        list_price=1_000_000,
        bedrooms_total=3,
        bathrooms_total_integer=2,
        living_area=2_000,
        public_remarks="Modern home.",
    )


class FakeSimilarityRetriever:
    def __init__(self) -> None:
        self.call_count = 0
        self.received_target = None
        self.received_top_k = None

    def recommend_similar(
        self,
        target_listing_id: str,
        top_k: int = 5,
    ):
        self.call_count += 1
        self.received_target = (
            target_listing_id
        )
        self.received_top_k = top_k

        return [
            {
                "listing": make_listing(
                    "A"
                ),
                "hybrid_similarity_score": 90.0,
                "structured_similarity_score": 60.0,
                "semantic_similarity": 0.75,
                "semantic_similarity_score": 30.0,
                "embedding_row": 1,
            },
            {
                "listing": make_listing(
                    "B"
                ),
                "hybrid_similarity_score": 80.0,
                "structured_similarity_score": 50.0,
                "semantic_similarity": 0.75,
                "semantic_similarity_score": 30.0,
                "embedding_row": 2,
            },
        ][:top_k]


class FakeMarketAgent:
    def __init__(
        self,
        should_fail: bool = False,
    ) -> None:
        self.call_count = 0
        self.should_fail = should_fail

    def analyze_listing(
        self,
        listing,
        months=12,
        market_limit=500,
        comparable_limit=100,
        minimum_comps=5,
    ):
        self.call_count += 1

        if self.should_fail:
            raise RuntimeError(
                "comp lookup failed"
            )

        return SimpleNamespace(
            comparable_market=(
                SimpleNamespace(
                    median_close_price=950_000,
                    median_price_per_sqft=475.0,
                    comp_count=10,
                    match_level="strict",
                )
            ),
            city_market=SimpleNamespace(),
        )


class FakeComparableValueAgent:
    def __init__(self) -> None:
        self.call_count = 0

    def run(
        self,
        listing,
        market_context,
    ):
        self.call_count += 1

        return SimpleNamespace(
            match_level="strict",
            comp_count=10,
            valid_ppsf_count=9,
            ppsf_coverage_ratio=0.9,
            asking_price_per_sqft=500.0,
            comparable_median_price_per_sqft=475.0,
            price_per_sqft_ratio=1.0526,
            adjusted_value_score=30.0,
            comparable_quality_score=93.0,
            signals=[
                "The asking price per square foot "
                "is moderately above comparable sales."
            ],
        )


def test_attaches_comp_validation() -> None:
    service = HybridRecommendationService(
        similarity_retriever=(
            FakeSimilarityRetriever()
        ),
        market_agent=FakeMarketAgent(),
        comparable_value_agent=(
            FakeComparableValueAgent()
        ),
    )

    results = service.recommend(
        target_listing_id="TARGET",
        top_k=2,
    )

    assert len(results) == 2

    validation = results[0][
        "comp_validation"
    ]

    assert (
        validation["status"]
        == "validated"
    )
    assert validation["comp_count"] == 10
    assert (
        validation["match_level"]
        == "strict"
    )
    assert (
        validation[
            "comparable_value_score"
        ]
        == 30.0
    )


def test_preserves_similarity_order() -> None:
    service = HybridRecommendationService(
        similarity_retriever=(
            FakeSimilarityRetriever()
        ),
        market_agent=FakeMarketAgent(),
        comparable_value_agent=(
            FakeComparableValueAgent()
        ),
    )

    results = service.recommend(
        target_listing_id="TARGET",
        top_k=2,
    )

    assert (
        results[0]["listing"].listing_key
        == "A"
    )
    assert (
        results[1]["listing"].listing_key
        == "B"
    )

    assert (
        results[0][
            "hybrid_similarity_score"
        ]
        > results[1][
            "hybrid_similarity_score"
        ]
    )


def test_validates_each_recommended_listing() -> None:
    market_agent = FakeMarketAgent()
    value_agent = (
        FakeComparableValueAgent()
    )

    service = HybridRecommendationService(
        similarity_retriever=(
            FakeSimilarityRetriever()
        ),
        market_agent=market_agent,
        comparable_value_agent=value_agent,
    )

    results = service.recommend(
        target_listing_id="TARGET",
        top_k=2,
    )

    assert len(results) == 2
    assert market_agent.call_count == 2
    assert value_agent.call_count == 2


def test_comp_failure_does_not_remove_recommendation() -> None:
    service = HybridRecommendationService(
        similarity_retriever=(
            FakeSimilarityRetriever()
        ),
        market_agent=FakeMarketAgent(
            should_fail=True
        ),
        comparable_value_agent=(
            FakeComparableValueAgent()
        ),
    )

    results = service.recommend(
        target_listing_id="TARGET",
        top_k=2,
    )

    assert len(results) == 2

    assert (
        results[0][
            "comp_validation"
        ]["status"]
        == "unavailable"
    )

    assert (
        results[0]["listing"].listing_key
        == "A"
    )


def test_rejects_invalid_top_k() -> None:
    service = HybridRecommendationService(
        similarity_retriever=(
            FakeSimilarityRetriever()
        ),
        market_agent=FakeMarketAgent(),
        comparable_value_agent=(
            FakeComparableValueAgent()
        ),
    )

    with pytest.raises(
        ValueError,
        match="top_k",
    ):
        service.recommend(
            target_listing_id="TARGET",
            top_k=0,
        )