import pytest

from src.orchestration.router import IntentRouter


ROUTING_CASES = [
    # ================================================================
    # SEARCH — 5 cases
    # ================================================================
    (
        "Find 3-bedroom homes under $900k in Irvine.",
        "search",
        ["search"],
    ),
    (
        "Show me condos in Pasadena with a pool.",
        "search",
        ["search"],
    ),
    (
        "Find houses under $1.2 million in Los Angeles.",
        "search",
        ["search"],
    ),
    (
        "I'm looking for townhouses in Santa Monica with a garage.",
        "search",
        ["search"],
    ),
    (
        "Show me 2-bedroom 2-bath homes in San Diego.",
        "search",
        ["search"],
    ),

    # ================================================================
    # MARKET — 5 cases
    # ================================================================
    (
        "What is the housing market like in Pasadena?",
        "market",
        ["market"],
    ),
    (
        "Are home prices rising in Irvine?",
        "market",
        ["market"],
    ),
    (
        "What is the median sale price in Santa Monica?",
        "market",
        ["market"],
    ),
    (
        "What is the average days on market in Los Angeles?",
        "market",
        ["market"],
    ),
    (
        "Is the Pasadena market warming or cooling?",
        "market",
        ["market"],
    ),

    # ================================================================
    # RECOMMEND — 5 cases
    # ================================================================
    (
        "Show me homes similar to this listing.",
        "recommend",
        ["recommend"],
    ),
    (
        "Find similar homes to listing ABC123.",
        "recommend",
        ["recommend"],
    ),
    (
        "Recommend similar properties to this listing.",
        "recommend",
        ["recommend"],
    ),
    (
        "Show me more like this.",
        "recommend",
        ["recommend"],
    ),
    (
        "Find alternatives similar to this property.",
        "recommend",
        ["recommend"],
    ),

    # ================================================================
    # KNOWLEDGE — 5 cases
    # ================================================================
    (
        "What does DaysOnMarket mean?",
        "knowledge",
        ["knowledge"],
    ),
    (
        "Define ClosePrice.",
        "knowledge",
        ["knowledge"],
    ),
    (
        "What does ListingKey mean?",
        "knowledge",
        ["knowledge"],
    ),
    (
        "Explain the field LivingArea.",
        "knowledge",
        ["knowledge"],
    ),
    (
        "What does AssociationFee mean?",
        "knowledge",
        ["knowledge"],
    ),

    # ================================================================
    # MIXED — 5 cases
    # ================================================================
    (
        "Find affordable homes in Pasadena and tell me whether "
        "prices are rising.",
        "mixed",
        ["search", "market"],
    ),
    (
        "Show me 2-bedroom condos in Irvine and give me market stats.",
        "mixed",
        ["search", "market"],
    ),
    (
        "Find houses under $1 million in Los Angeles and tell me "
        "the average days on market.",
        "mixed",
        ["search", "market"],
    ),
    (
        "I'm looking for townhouses in Pasadena. "
        "Are prices going up?",
        "mixed",
        ["search", "market"],
    ),
    (
        "Show me homes with a pool in Santa Monica and tell me "
        "whether the market is cooling.",
        "mixed",
        ["search", "market"],
    ),
]


@pytest.mark.parametrize(
    (
        "query",
        "expected_route",
        "expected_routes",
    ),
    ROUTING_CASES,
)
def test_router_classifies_query_correctly(
    query: str,
    expected_route: str,
    expected_routes: list[str],
) -> None:
    router = IntentRouter()

    decision = router.route(query)

    assert decision.route == expected_route
    assert decision.routes == expected_routes
    assert decision.reason