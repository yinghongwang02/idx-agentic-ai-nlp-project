from __future__ import annotations

from dataclasses import dataclass
from math import isclose


@dataclass(frozen=True)
class RecommendationConfig:
    """
    Typed and validated recommendation scoring configuration.

    The three component weights must be non-negative and sum to 1.0.

    Label thresholds must satisfy:

        0 <= moderate < good < strong <= 100
    """

    preference_weight: float = 0.40
    comparable_value_weight: float = 0.35
    negotiation_weight: float = 0.25

    strong_match_threshold: float = 80.0
    good_match_threshold: float = 65.0
    moderate_match_threshold: float = 50.0

    def __post_init__(self) -> None:
        self._validate_weights()
        self._validate_thresholds()

    def _validate_weights(self) -> None:
        weights = (
            self.preference_weight,
            self.comparable_value_weight,
            self.negotiation_weight,
        )

        if any(weight < 0.0 for weight in weights):
            raise ValueError(
                "Recommendation weights must be non-negative."
            )

        if not isclose(
            sum(weights),
            1.0,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "Recommendation weights must sum to 1.0."
            )

    def _validate_thresholds(self) -> None:
        if not (
            0.0
            <= self.moderate_match_threshold
            < self.good_match_threshold
            < self.strong_match_threshold
            <= 100.0
        ):
            raise ValueError(
                "Recommendation thresholds must satisfy "
                "0 <= moderate < good < strong <= 100."
            )