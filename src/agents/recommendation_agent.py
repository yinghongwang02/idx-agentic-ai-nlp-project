from __future__ import annotations

from src.config.recommendation_config import (
    RecommendationConfig,
)
from src.schemas.comparable_value_analysis_schema import (
    ComparableValueAnalysis,
)
from src.schemas.listing_schema import ListingSchema
from src.schemas.negotiation_analysis_schema import (
    NegotiationAnalysis,
)
from src.schemas.preference_match_analysis_schema import (
    PreferenceMatchAnalysis,
)
from src.schemas.recommendation_score_schema import (
    RecommendationScore,
)


class RecommendationAgent:
    """
    Aggregate listing-level recommendation signals and rank
    candidate listings using a configurable scoring policy.
    """

    def __init__(
        self,
        config: RecommendationConfig | None = None,
    ) -> None:
        self.config = (
            config
            if config is not None
            else RecommendationConfig()
        )

    def score_listing(
        self,
        listing: ListingSchema,
        preference_analysis: PreferenceMatchAnalysis,
        comparable_value_analysis: ComparableValueAnalysis,
        negotiation_analysis: NegotiationAnalysis,
    ) -> RecommendationScore:
        overall_score = (
            preference_analysis.preference_match_score
            * self.config.preference_weight
            + comparable_value_analysis.adjusted_value_score
            * self.config.comparable_value_weight
            + negotiation_analysis.negotiation_score
            * self.config.negotiation_weight
        )

        overall_score = round(
            overall_score,
            2,
        )

        return RecommendationScore(
            listing=listing,
            overall_score=overall_score,
            preference_match_score=(
                preference_analysis.preference_match_score
            ),
            comparable_value_score=(
                comparable_value_analysis.adjusted_value_score
            ),
            negotiation_score=(
                negotiation_analysis.negotiation_score
            ),
            recommendation_label=(
                self._get_recommendation_label(
                    overall_score=overall_score,
                )
            ),
            reasons=self._build_reasons(
                preference_analysis=preference_analysis,
                comparable_value_analysis=(
                    comparable_value_analysis
                ),
                negotiation_analysis=negotiation_analysis,
            ),
        )

    def rank(
        self,
        recommendations: list[RecommendationScore],
        limit: int = 5,
    ) -> list[RecommendationScore]:
        """
        Rank recommendations deterministically.

        Overall score is the primary key. Listing key is used as a
        deterministic tie-breaker when scores are equal.
        """
        ranked = sorted(
            recommendations,
            key=lambda recommendation: (
                -recommendation.overall_score,
                recommendation.listing.listing_key,
            ),
        )

        return ranked[:limit]

    def _get_recommendation_label(
        self,
        overall_score: float,
    ) -> str:
        if (
            overall_score
            >= self.config.strong_match_threshold
        ):
            return "Strong Match"

        if (
            overall_score
            >= self.config.good_match_threshold
        ):
            return "Good Match"

        if (
            overall_score
            >= self.config.moderate_match_threshold
        ):
            return "Moderate Match"

        return "Limited Match"

    @staticmethod
    def _build_reasons(
        preference_analysis: PreferenceMatchAnalysis,
        comparable_value_analysis: ComparableValueAnalysis,
        negotiation_analysis: NegotiationAnalysis,
    ) -> list[str]:
        reasons: list[str] = []

        reasons.extend(
            preference_analysis.signals
        )

        reasons.extend(
            comparable_value_analysis.signals
        )

        reasons.extend(
            negotiation_analysis.signals
        )

        return reasons