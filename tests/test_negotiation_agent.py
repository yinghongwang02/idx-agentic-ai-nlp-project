from types import SimpleNamespace

from src.agents.negotiation_agent import NegotiationAgent
from src.schemas.listing_schema import ListingSchema


def make_listing(
    days_on_market: int | None,
) -> ListingSchema:
    return ListingSchema(
        listing_key="TEST-001",
        unparsed_address="1 Test Street",
        city="Irvine",
        list_price=1_000_000,
        days_on_market=days_on_market,
    )


def make_market_context(
    comparable_match_level: str = "strict",
    comparable_comp_count: int = 10,
    comparable_dom: float | None = 30.0,
    comparable_sale_to_list: float | None = 0.97,
    city_dom: float | None = 40.0,
    city_sale_to_list: float | None = 0.99,
):
    return SimpleNamespace(
        comparable_market=SimpleNamespace(
            match_level=comparable_match_level,
            comp_count=comparable_comp_count,
            average_days_on_market=comparable_dom,
            average_sale_to_list_ratio=(
                comparable_sale_to_list
            ),
        ),
        city_market=SimpleNamespace(
            average_days_on_market=city_dom,
            average_sale_to_list_ratio=(
                city_sale_to_list
            ),
        ),
    )


def test_negotiation_agent_uses_comparable_market_when_available() -> None:
    agent = NegotiationAgent()

    # Listing DOM 60 vs comparable DOM 30 => ratio 2.0 => DOM score 100.
    # Comparable sale-to-list 0.97 => sale-to-list score 80.
    # Overall = 100*0.65 + 80*0.35 = 93.
    analysis = agent.run(
        listing=make_listing(
            days_on_market=60,
        ),
        market_context=make_market_context(),
    )

    assert analysis.dom_score == 100.0
    assert analysis.sale_to_list_score == 80.0
    assert analysis.negotiation_score == 93.0

    assert any(
        "10 strict comparable sales"
        in signal
        for signal in analysis.signals
    )


def test_negotiation_agent_falls_back_to_city_market() -> None:
    agent = NegotiationAgent()

    # market_fallback forces city-level references.
    # Listing DOM 40 / city DOM 40 = 1.0 => DOM score 50.
    # City sale-to-list 0.99 => score 60.
    # Overall = 50*0.65 + 60*0.35 = 53.5.
    analysis = agent.run(
        listing=make_listing(
            days_on_market=40,
        ),
        market_context=make_market_context(
            comparable_match_level="market_fallback",
            comparable_comp_count=20,
            comparable_dom=10.0,
            comparable_sale_to_list=0.90,
            city_dom=40.0,
            city_sale_to_list=0.99,
        ),
    )

    assert analysis.dom_score == 50.0
    assert analysis.sale_to_list_score == 60.0
    assert analysis.negotiation_score == 53.5

    assert any(
        "broader city market data is used"
        in signal
        for signal in analysis.signals
    )


def test_negotiation_agent_falls_back_when_no_comparable_sales() -> None:
    agent = NegotiationAgent()

    analysis = agent.run(
        listing=make_listing(
            days_on_market=80,
        ),
        market_context=make_market_context(
            comparable_match_level="strict",
            comparable_comp_count=0,
            city_dom=40.0,
            city_sale_to_list=0.94,
        ),
    )

    # 80 / 40 = 2.0 => DOM 100.
    # 0.94 => sale-to-list 100.
    assert analysis.dom_score == 100.0
    assert analysis.sale_to_list_score == 100.0
    assert analysis.negotiation_score == 100.0


def test_negotiation_agent_handles_missing_market_data_neutrally() -> None:
    agent = NegotiationAgent()

    analysis = agent.run(
        listing=make_listing(
            days_on_market=None,
        ),
        market_context=make_market_context(
            comparable_match_level="market_fallback",
            comparable_comp_count=0,
            city_dom=None,
            city_sale_to_list=None,
        ),
    )

    assert analysis.dom_score == 50.0
    assert analysis.sale_to_list_score == 50.0
    assert analysis.negotiation_score == 50.0

    assert any(
        "insufficient"
        in signal.lower()
        for signal in analysis.signals
    )


def test_negotiation_agent_scores_newer_listing_lower() -> None:
    agent = NegotiationAgent()

    analysis = agent.run(
        listing=make_listing(
            days_on_market=10,
        ),
        market_context=make_market_context(
            comparable_dom=30.0,
            comparable_sale_to_list=1.03,
        ),
    )

    # 10 / 30 < 0.4 => DOM score 20.
    # Sale-to-list > 1.02 => score 20.
    # Overall = 20.
    assert analysis.dom_score == 20.0
    assert analysis.sale_to_list_score == 20.0
    assert analysis.negotiation_score == 20.0

    assert any(
        "relatively new"
        in signal.lower()
        for signal in analysis.signals
    )