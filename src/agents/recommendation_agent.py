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
    Aggregate listing-level recommendation signals
    and rank candidate listings.
    """

    PREFERENCE_WEIGHT = 0.40
    COMPARABLE_VALUE_WEIGHT = 0.35
    NEGOTIATION_WEIGHT = 0.25

    def score_listing(
        self,
        listing: ListingSchema,
        preference_analysis: PreferenceMatchAnalysis,
        comparable_value_analysis: ComparableValueAnalysis,
        negotiation_analysis: NegotiationAnalysis,
    ) -> RecommendationScore:
        overall_score = (
            preference_analysis.preference_match_score
            * self.PREFERENCE_WEIGHT
            + comparable_value_analysis.adjusted_value_score
            * self.COMPARABLE_VALUE_WEIGHT
            + negotiation_analysis.negotiation_score
            * self.NEGOTIATION_WEIGHT
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
        ranked = sorted(
            recommendations,
            key=lambda recommendation: (
                recommendation.overall_score
            ),
            reverse=True,
        )

        return ranked[:limit]

    @staticmethod
    def _get_recommendation_label(
        overall_score: float,
    ) -> str:
        if overall_score >= 80:
            return "Strong Match"

        if overall_score >= 65:
            return "Good Match"

        if overall_score >= 50:
            return "Moderate Match"

        return "Limited Match"

    @staticmethod
    def _build_reasons(
        preference_analysis: PreferenceMatchAnalysis,
        comparable_value_analysis: ComparableValueAnalysis,
        negotiation_analysis: NegotiationAnalysis,
    ) -> list[str]:
        reasons = []

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