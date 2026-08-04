from __future__ import annotations

import pytest

from src.config.recommendation_config import (
    RecommendationConfig,
)


def test_default_recommendation_config_preserves_policy(
) -> None:
    config = RecommendationConfig()

    assert config.preference_weight == 0.40
    assert config.comparable_value_weight == 0.35
    assert config.negotiation_weight == 0.25

    assert config.strong_match_threshold == 80.0
    assert config.good_match_threshold == 65.0
    assert config.moderate_match_threshold == 50.0


def test_recommendation_weights_sum_to_one() -> None:
    config = RecommendationConfig()

    total_weight = (
        config.preference_weight
        + config.comparable_value_weight
        + config.negotiation_weight
    )

    assert total_weight == pytest.approx(1.0)


def test_custom_recommendation_config_is_accepted(
) -> None:
    config = RecommendationConfig(
        preference_weight=0.50,
        comparable_value_weight=0.30,
        negotiation_weight=0.20,
        strong_match_threshold=90.0,
        good_match_threshold=75.0,
        moderate_match_threshold=60.0,
    )

    assert config.preference_weight == 0.50
    assert config.comparable_value_weight == 0.30
    assert config.negotiation_weight == 0.20

    assert config.strong_match_threshold == 90.0
    assert config.good_match_threshold == 75.0
    assert config.moderate_match_threshold == 60.0


def test_negative_weight_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="must be non-negative",
    ):
        RecommendationConfig(
            preference_weight=-0.10,
            comparable_value_weight=0.60,
            negotiation_weight=0.50,
        )


def test_weights_not_summing_to_one_are_rejected(
) -> None:
    with pytest.raises(
        ValueError,
        match="must sum to 1.0",
    ):
        RecommendationConfig(
            preference_weight=0.50,
            comparable_value_weight=0.40,
            negotiation_weight=0.30,
        )


@pytest.mark.parametrize(
    (
        "moderate_threshold",
        "good_threshold",
        "strong_threshold",
    ),
    [
        (-1.0, 65.0, 80.0),
        (50.0, 50.0, 80.0),
        (65.0, 60.0, 80.0),
        (50.0, 80.0, 80.0),
        (50.0, 85.0, 80.0),
        (50.0, 65.0, 101.0),
    ],
)
def test_invalid_threshold_order_is_rejected(
    moderate_threshold: float,
    good_threshold: float,
    strong_threshold: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="thresholds must satisfy",
    ):
        RecommendationConfig(
            moderate_match_threshold=(
                moderate_threshold
            ),
            good_match_threshold=good_threshold,
            strong_match_threshold=strong_threshold,
        )