from __future__ import annotations

from typing import Any

import pytest

from src.agents.search_agent import SearchAgent
from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema
from src.schemas.recommendation_score_schema import (
    RecommendationScore,
)
from src.search.mysql_search_repository import (
    MySQLSearchRepository,
)
from src.workflow.graph import PropertySearchGraph


pytestmark = pytest.mark.integration


TEST_QUERY = (
    "Find 3 bedroom homes in Irvine with a garage, "
    "preferably with a pool."
)


def _recommendation_signature(
    recommendation: RecommendationScore,
) -> dict[str, Any]:
    return {
        "listing_key": recommendation.listing.listing_key,
        "overall_score": recommendation.overall_score,
        "preference_match_score": (
            recommendation.preference_match_score
        ),
        "comparable_value_score": (
            recommendation.comparable_value_score
        ),
        "negotiation_score": (
            recommendation.negotiation_score
        ),
        "recommendation_label": (
            recommendation.recommendation_label
        ),
        "reasons": list(recommendation.reasons),
    }


def _ranked_signatures(
    recommendations: list[RecommendationScore],
) -> list[dict[str, Any]]:
    return [
        _recommendation_signature(recommendation)
        for recommendation in recommendations
    ]


@pytest.fixture(scope="module")
def workflow() -> PropertySearchGraph:
    search_agent = SearchAgent(
        repository=MySQLSearchRepository(),
    )

    return PropertySearchGraph(
        search_agent=search_agent,
        parallel_candidate_analysis=True,
        max_parallel_candidates=4,
    )


@pytest.fixture(scope="module")
def intent_and_candidates(
    workflow: PropertySearchGraph,
) -> tuple[
    PropertyIntent,
    list[ListingSchema],
]:
    intent = workflow.intent_agent.run(
        TEST_QUERY
    )

    candidates = workflow.search_agent.run(
        intent,
        limit=workflow.SEARCH_CANDIDATE_LIMIT,
    )

    assert candidates, (
        "The consistency test requires at least one "
        "candidate listing."
    )

    return intent, candidates


@pytest.fixture(scope="module")
def consistency_results(
    workflow: PropertySearchGraph,
    intent_and_candidates: tuple[
        PropertyIntent,
        list[ListingSchema],
    ],
) -> tuple[
    list[ListingSchema],
    list[RecommendationScore],
    list[RecommendationScore],
]:
    intent, candidates = intent_and_candidates

    (
        sequential_scores,
        sequential_errors,
    ) = workflow._analyze_candidates_sequentially(
        listings=candidates,
        intent=intent,
    )

    (
        parallel_scores,
        parallel_errors,
    ) = workflow._analyze_candidates_in_parallel(
        listings=candidates,
        intent=intent,
    )

    assert sequential_errors == []
    assert parallel_errors == []

    return (
        candidates,
        sequential_scores,
        parallel_scores,
    )

def test_parallel_and_sequential_outputs_match(
    workflow: PropertySearchGraph,
    consistency_results: tuple[
        list[ListingSchema],
        list[RecommendationScore],
        list[RecommendationScore],
    ],
) -> None:
    """
    Verify that execution strategy does not change the final
    Top-K recommendation results or ranking.
    """
    (
        _,
        sequential_scores,
        parallel_scores,
    ) = consistency_results

    sequential_ranked = (
        workflow.recommendation_agent.rank(
            recommendations=sequential_scores,
            limit=workflow.RECOMMENDATION_LIMIT,
        )
    )

    parallel_ranked = (
        workflow.recommendation_agent.rank(
            recommendations=parallel_scores,
            limit=workflow.RECOMMENDATION_LIMIT,
        )
    )

    assert _ranked_signatures(
        parallel_ranked
    ) == _ranked_signatures(
        sequential_ranked
    )


def test_parallel_and_sequential_analyze_same_candidates(
    consistency_results: tuple[
        list[ListingSchema],
        list[RecommendationScore],
        list[RecommendationScore],
    ],
) -> None:
    """
    Verify that parallel analysis does not lose, duplicate, or add
    candidate recommendations.
    """
    (
        candidates,
        sequential_scores,
        parallel_scores,
    ) = consistency_results

    candidate_keys = {
        listing.listing_key
        for listing in candidates
    }

    sequential_keys = {
        recommendation.listing.listing_key
        for recommendation in sequential_scores
    }

    parallel_keys = {
        recommendation.listing.listing_key
        for recommendation in parallel_scores
    }

    assert sequential_keys == candidate_keys
    assert parallel_keys == candidate_keys

    assert len(sequential_scores) == len(candidates)
    assert len(parallel_scores) == len(candidates)


def test_parallel_component_scores_match_sequential(
    consistency_results: tuple[
        list[ListingSchema],
        list[RecommendationScore],
        list[RecommendationScore],
    ],
) -> None:
    """
    Verify that every candidate receives the same component scores,
    label, and reasons in sequential and parallel execution.
    """
    (
        _,
        sequential_scores,
        parallel_scores,
    ) = consistency_results

    sequential_by_key = {
        recommendation.listing.listing_key: (
            _recommendation_signature(
                recommendation
            )
        )
        for recommendation in sequential_scores
    }

    parallel_by_key = {
        recommendation.listing.listing_key: (
            _recommendation_signature(
                recommendation
            )
        )
        for recommendation in parallel_scores
    }

    assert parallel_by_key == sequential_by_key