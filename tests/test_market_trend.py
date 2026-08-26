from src.agents.market_agent import MarketAgent


def test_market_direction_warming() -> None:
    direction = MarketAgent._classify_market_direction(
        recent_comp_count=100,
        previous_comp_count=100,
        minimum_period_comps=10,
        median_price_change_pct=0.04,
        median_ppsf_change_pct=0.05,
        average_dom_change=-8.0,
        sale_to_list_change=0.015,
    )

    assert direction == "warming"


def test_market_direction_cooling() -> None:
    direction = MarketAgent._classify_market_direction(
        recent_comp_count=100,
        previous_comp_count=100,
        minimum_period_comps=10,
        median_price_change_pct=-0.04,
        median_ppsf_change_pct=-0.03,
        average_dom_change=9.0,
        sale_to_list_change=-0.015,
    )

    assert direction == "cooling"


def test_market_direction_stable() -> None:
    direction = MarketAgent._classify_market_direction(
        recent_comp_count=100,
        previous_comp_count=100,
        minimum_period_comps=10,
        median_price_change_pct=0.005,
        median_ppsf_change_pct=-0.004,
        average_dom_change=1.0,
        sale_to_list_change=0.002,
    )

    assert direction == "stable"


def test_market_direction_insufficient_data() -> None:
    direction = MarketAgent._classify_market_direction(
        recent_comp_count=5,
        previous_comp_count=100,
        minimum_period_comps=10,
        median_price_change_pct=0.10,
        median_ppsf_change_pct=0.10,
        average_dom_change=-20.0,
        sale_to_list_change=0.05,
    )

    assert direction == "insufficient_data"


def test_market_direction_requires_at_least_two_valid_signals() -> None:
    direction = MarketAgent._classify_market_direction(
        recent_comp_count=100,
        previous_comp_count=100,
        minimum_period_comps=10,
        median_price_change_pct=0.05,
        median_ppsf_change_pct=None,
        average_dom_change=None,
        sale_to_list_change=None,
    )

    assert direction == "insufficient_data"


def test_market_direction_one_warming_one_cooling_is_stable() -> None:
    direction = MarketAgent._classify_market_direction(
        recent_comp_count=100,
        previous_comp_count=100,
        minimum_period_comps=10,
        median_price_change_pct=0.04,
        median_ppsf_change_pct=-0.04,
        average_dom_change=0.0,
        sale_to_list_change=0.0,
    )

    assert direction == "stable"

def test_market_direction_warming_at_threshold() -> None:
    direction = MarketAgent._classify_market_direction(
        recent_comp_count=50,
        previous_comp_count=50,
        minimum_period_comps=10,
        median_price_change_pct=0.02,
        median_ppsf_change_pct=0.02,
        average_dom_change=0.0,
        sale_to_list_change=0.0,
    )

    assert direction == "warming"


def test_market_direction_stable_inside_neutral_band() -> None:
    direction = MarketAgent._classify_market_direction(
        recent_comp_count=50,
        previous_comp_count=50,
        minimum_period_comps=10,
        median_price_change_pct=0.019,
        median_ppsf_change_pct=-0.019,
        average_dom_change=4.9,
        sale_to_list_change=-0.009,
    )

    assert direction == "stable"