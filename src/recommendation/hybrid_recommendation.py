from __future__ import annotations

from typing import Any

from src.agents.comparable_value_agent import (
    ComparableValueAgent,
)
from src.agents.market_agent import MarketAgent
from src.recommendation.hybrid_similarity import (
    SimilarListingRetriever,
)


class HybridRecommendationService:
    """
    Combine listing-to-listing hybrid similarity retrieval with
    sold-comparable price validation.

    Responsibilities:
        1. Retrieve active listings similar to a target listing.
        2. Validate each retrieved listing against recent sold comps.
        3. Preserve the original hybrid-similarity ranking.

    This service intentionally does not replace the existing
    RecommendationAgent or PropertyAnalysisSubgraph.
    """

    def __init__(
        self,
        similarity_retriever: SimilarListingRetriever,
        market_agent: MarketAgent,
        comparable_value_agent: ComparableValueAgent,
    ) -> None:
        self.similarity_retriever = similarity_retriever
        self.market_agent = market_agent
        self.comparable_value_agent = (
            comparable_value_agent
        )

    def recommend(
        self,
        target_listing_id: str,
        top_k: int = 5,
        months: int = 12,
        market_limit: int = 500,
        comparable_limit: int = 100,
        minimum_comps: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Return hybrid-similar active listings with sold-comp
        price validation.

        Hybrid similarity determines ranking.

        Sold-comparable analysis is attached as validation evidence
        and does not modify the 60/40 similarity score.
        """
        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        similarity_results = (
            self.similarity_retriever.recommend_similar(
                target_listing_id=target_listing_id,
                top_k=top_k,
            )
        )

        validated_results: list[
            dict[str, Any]
        ] = []

        for result in similarity_results:
            listing = result["listing"]

            try:
                market_context = (
                    self.market_agent.analyze_listing(
                        listing=listing,
                        months=months,
                        market_limit=market_limit,
                        comparable_limit=(
                            comparable_limit
                        ),
                        minimum_comps=minimum_comps,
                    )
                )

                value_analysis = (
                    self.comparable_value_agent.run(
                        listing=listing,
                        market_context=market_context,
                    )
                )

                comparable_market = (
                    market_context.comparable_market
                )

                validation = {
                    "status": "validated",
                    "match_level": (
                        value_analysis.match_level
                    ),
                    "comp_count": (
                        value_analysis.comp_count
                    ),
                    "valid_ppsf_count": (
                        value_analysis.valid_ppsf_count
                    ),
                    "ppsf_coverage_ratio": (
                        value_analysis.ppsf_coverage_ratio
                    ),
                    "asking_price_per_sqft": (
                        value_analysis
                        .asking_price_per_sqft
                    ),
                    "comparable_median_price_per_sqft": (
                        value_analysis
                        .comparable_median_price_per_sqft
                    ),
                    "price_per_sqft_ratio": (
                        value_analysis
                        .price_per_sqft_ratio
                    ),
                    "comparable_median_close_price": (
                        comparable_market
                        .median_close_price
                    ),
                    "comparable_value_score": (
                        value_analysis
                        .adjusted_value_score
                    ),
                    "comparable_quality_score": (
                        value_analysis
                        .comparable_quality_score
                    ),
                    "signals": list(
                        value_analysis.signals
                    ),
                }

            except Exception as exc:
                # Comp-validation failure should not destroy an
                # otherwise valid similar-listing recommendation.
                validation = {
                    "status": "unavailable",
                    "match_level": None,
                    "comp_count": 0,
                    "valid_ppsf_count": 0,
                    "ppsf_coverage_ratio": 0.0,
                    "asking_price_per_sqft": None,
                    "comparable_median_price_per_sqft": None,
                    "price_per_sqft_ratio": None,
                    "comparable_median_close_price": None,
                    "comparable_value_score": None,
                    "comparable_quality_score": None,
                    "signals": [
                        "Sold-comparable validation "
                        "was unavailable."
                    ],
                    "error": str(exc),
                }

            validated_results.append(
                {
                    **result,
                    "comp_validation": validation,
                }
            )

        return validated_results