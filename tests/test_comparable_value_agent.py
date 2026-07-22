from types import SimpleNamespace

from src.agents.comparable_value_agent import ComparableValueAgent
from src.schemas.listing_schema import ListingSchema


def make_listing(
    list_price: float = 1_000_000,
    living_area: float = 2_000,
) -> ListingSchema:
    return ListingSchema(
        listing_key="TEST-001",
        unparsed_address="1 Test Street",
        city="Irvine",
        list_price=list_price,
        living_area=living_area,
    )


def make_market_context(
    median_price_per_sqft: float | None,
    match_level: str = "strict",
    comp_count: int = 10,
):
    return SimpleNamespace(
        comparable_market=SimpleNamespace(
            median_price_per_sqft=median_price_per_sqft,
            match_level=match_level,
            comp_count=comp_count,
        ),
    )


def test_comparable_value_agent_scores_strong_relative_value() -> None:
    agent = ComparableValueAgent()

    # Asking PPSF = 1,000,000 / 2,000 = 500.
    # Comparable PPSF = 600.
    # Ratio = 0.8333, which maps to a raw value score of 100.
    analysis = agent.run(
        listing=make_listing(),
        market_context=make_market_context(
            median_price_per_sqft=600.0,
            match_level="strict",
            comp_count=10,
        ),
    )

    assert analysis.asking_price_per_sqft == 500.0
    assert analysis.comparable_median_price_per_sqft == 600.0
    assert analysis.price_per_sqft_ratio == 0.8333
    assert analysis.raw_value_score == 100.0

    # strict=100, count>=10=85, full coverage=100
    # quality = 100*0.50 + 85*0.30 + 100*0.20 = 95.5
    assert analysis.comparable_quality_score == 95.5

    # Adjust raw score toward neutral 50 using 95.5% confidence.
    assert analysis.adjusted_value_score == 97.75

    assert any(
        "substantially below comparable sales"
        in signal
        for signal in analysis.signals
    )


def test_comparable_value_agent_scores_neutral_when_ppsf_is_close() -> None:
    agent = ComparableValueAgent()

    # Asking PPSF and comparable PPSF are both 500.
    analysis = agent.run(
        listing=make_listing(),
        market_context=make_market_context(
            median_price_per_sqft=500.0,
            match_level="strict",
            comp_count=10,
        ),
    )

    assert analysis.price_per_sqft_ratio == 1.0
    assert analysis.raw_value_score == 50.0
    assert analysis.adjusted_value_score == 50.0

    assert any(
        "close to comparable sales"
        in signal
        for signal in analysis.signals
    )


def test_comparable_value_agent_reduces_confidence_for_weaker_comps() -> None:
    agent = ComparableValueAgent()

    strong_analysis = agent.run(
        listing=make_listing(),
        market_context=make_market_context(
            median_price_per_sqft=600.0,
            match_level="strict",
            comp_count=20,
        ),
    )

    weak_analysis = agent.run(
        listing=make_listing(),
        market_context=make_market_context(
            median_price_per_sqft=600.0,
            match_level="market_fallback",
            comp_count=2,
        ),
    )

    assert strong_analysis.raw_value_score == 100.0
    assert weak_analysis.raw_value_score == 100.0

    assert (
        strong_analysis.comparable_quality_score
        > weak_analysis.comparable_quality_score
    )

    assert (
        strong_analysis.adjusted_value_score
        > weak_analysis.adjusted_value_score
    )

    assert (
        weak_analysis.adjusted_value_score
        > 50.0
    )


def test_comparable_value_agent_handles_missing_ppsf_data() -> None:
    agent = ComparableValueAgent()

    analysis = agent.run(
        listing=make_listing(
            living_area=0,
        ),
        market_context=make_market_context(
            median_price_per_sqft=None,
            match_level="market_fallback",
            comp_count=0,
        ),
    )

    assert analysis.asking_price_per_sqft is None
    assert analysis.comparable_median_price_per_sqft is None
    assert analysis.price_per_sqft_ratio is None

    assert analysis.raw_value_score == 50.0
    assert analysis.valid_ppsf_count == 0
    assert analysis.ppsf_coverage_ratio == 0.0

    # Neutral raw score remains neutral regardless of confidence.
    assert analysis.adjusted_value_score == 50.0

    assert any(
        "insufficient"
        in signal.lower()
        for signal in analysis.signals
    )


def test_comparable_value_agent_reports_expected_quality_metadata() -> None:
    agent = ComparableValueAgent()

    analysis = agent.run(
        listing=make_listing(),
        market_context=make_market_context(
            median_price_per_sqft=550.0,
            match_level="relaxed",
            comp_count=5,
        ),
    )

    assert analysis.match_level == "relaxed"
    assert analysis.comp_count == 5
    assert analysis.valid_ppsf_count == 5
    assert analysis.ppsf_coverage_ratio == 1.0

    # relaxed=80, count>=5=70, coverage=100
    # quality = 40 + 21 + 20 = 81
    assert analysis.comparable_quality_score == 81.0