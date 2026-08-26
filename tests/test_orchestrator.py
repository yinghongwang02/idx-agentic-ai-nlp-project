from src.orchestration.orchestrator import (
    Orchestrator,
)
from src.schemas.orchestrator_state_schema import (
    RouterDecision,
)

def build_orchestrator(
    *,
    router,
    search_handler=lambda state: "search result",
    market_handler=lambda state: "market result",
    recommendation_handler=lambda state: "recommend result",
    knowledge_handler=lambda state: "knowledge result",
):
    return Orchestrator(
        router=router,
        search_handler=search_handler,
        market_handler=market_handler,
        recommendation_handler=(
            recommendation_handler
        ),
        knowledge_handler=knowledge_handler,
    )


def test_mixed_route_runs_search_and_market():
    def fake_router(
        query: str,
    ) -> RouterDecision:
        return RouterDecision(
            route="mixed",
            routes=[
                "search",
                "market",
            ],
            reason=(
                "Query requests property search "
                "and market analysis."
            ),
        )

    def fake_search(state):
        return {
            "listings": [
                "listing-1",
                "listing-2",
            ],
        }

    def fake_market(state):
        return {
            "trend": "rising",
        }

    def fake_recommend(state):
        return {
            "recommendations": [],
        }

    def fake_knowledge(state):
        return {
            "answer": "test",
        }

    orchestrator = Orchestrator(
        router=fake_router,
        search_handler=fake_search,
        market_handler=fake_market,
        recommendation_handler=(
            fake_recommend
        ),
        knowledge_handler=fake_knowledge,
    )

    result = orchestrator.invoke(
        (
            "Find affordable homes in Pasadena "
            "and tell me whether prices are rising."
        ),
        session_id="test-session",
    )

    assert result["route"] == "mixed"

    assert result["routes"] == [
        "search",
        "market",
    ]

    assert set(
        result["agents_invoked"]
    ) == {
        "search",
        "market",
    }

    assert result["search_result"] == {
        "listings": [
            "listing-1",
            "listing-2",
        ],
    }

    assert result["market_result"] == {
        "trend": "rising",
    }

    assert "Property Search:" in (
        result["final_response"]
    )

    assert "Market Analysis:" in (
        result["final_response"]
    )

def test_search_route_runs_only_search():
    calls = {
        "search": 0,
        "market": 0,
        "recommend": 0,
        "knowledge": 0,
    }

    def fake_router(
        query: str,
    ) -> RouterDecision:
        return RouterDecision(
            route="search",
            routes=["search"],
            reason="Property search request.",
        )

    def fake_search(state):
        calls["search"] += 1
        return "Found 5 homes in Irvine."

    def fake_market(state):
        calls["market"] += 1
        return "market"

    def fake_recommend(state):
        calls["recommend"] += 1
        return "recommend"

    def fake_knowledge(state):
        calls["knowledge"] += 1
        return "knowledge"

    orchestrator = build_orchestrator(
        router=fake_router,
        search_handler=fake_search,
        market_handler=fake_market,
        recommendation_handler=fake_recommend,
        knowledge_handler=fake_knowledge,
    )

    result = orchestrator.invoke(
        "Find homes in Irvine."
    )

    assert result["route"] == "search"
    assert result["routes"] == ["search"]

    assert result["agents_invoked"] == [
        "search"
    ]

    assert result["search_result"] == (
        "Found 5 homes in Irvine."
    )

    assert result["final_response"] == (
        "Found 5 homes in Irvine."
    )

    assert calls == {
        "search": 1,
        "market": 0,
        "recommend": 0,
        "knowledge": 0,
    }

def test_market_route_runs_only_market():
    calls = {
        "search": 0,
        "market": 0,
        "recommend": 0,
        "knowledge": 0,
    }

    def fake_router(
        query: str,
    ) -> RouterDecision:
        return RouterDecision(
            route="market",
            routes=["market"],
            reason="Market analysis request.",
        )

    def fake_search(state):
        calls["search"] += 1
        return "search"

    def fake_market(state):
        calls["market"] += 1
        return {
            "city": "Pasadena",
            "trend": "rising",
        }

    def fake_recommend(state):
        calls["recommend"] += 1
        return "recommend"

    def fake_knowledge(state):
        calls["knowledge"] += 1
        return "knowledge"

    orchestrator = build_orchestrator(
        router=fake_router,
        search_handler=fake_search,
        market_handler=fake_market,
        recommendation_handler=fake_recommend,
        knowledge_handler=fake_knowledge,
    )

    result = orchestrator.invoke(
        "Are Pasadena home prices rising?"
    )

    assert result["route"] == "market"

    assert result["agents_invoked"] == [
        "market"
    ]

    assert result["market_result"] == {
        "city": "Pasadena",
        "trend": "rising",
    }

    assert calls == {
        "search": 0,
        "market": 1,
        "recommend": 0,
        "knowledge": 0,
    }

def test_recommend_route_runs_only_recommendation():
    calls = {
        "search": 0,
        "market": 0,
        "recommend": 0,
        "knowledge": 0,
    }

    def fake_router(
        query: str,
    ) -> RouterDecision:
        return RouterDecision(
            route="recommend",
            routes=["recommend"],
            reason="Similar-home recommendation request.",
        )

    def fake_search(state):
        calls["search"] += 1
        return "search"

    def fake_market(state):
        calls["market"] += 1
        return "market"

    def fake_recommend(state):
        calls["recommend"] += 1
        return {
            "target_listing_id": "TEST-001",
            "recommendations": [
                "TEST-002",
                "TEST-003",
            ],
        }

    def fake_knowledge(state):
        calls["knowledge"] += 1
        return "knowledge"

    orchestrator = build_orchestrator(
        router=fake_router,
        search_handler=fake_search,
        market_handler=fake_market,
        recommendation_handler=fake_recommend,
        knowledge_handler=fake_knowledge,
    )

    result = orchestrator.invoke(
        "Show me homes similar to TEST-001."
    )

    assert result["route"] == "recommend"

    assert result["agents_invoked"] == [
        "recommend"
    ]

    assert result[
        "recommendation_result"
    ] == {
        "target_listing_id": "TEST-001",
        "recommendations": [
            "TEST-002",
            "TEST-003",
        ],
    }

    assert calls == {
        "search": 0,
        "market": 0,
        "recommend": 1,
        "knowledge": 0,
    }

def test_knowledge_route_runs_only_knowledge():
    calls = {
        "search": 0,
        "market": 0,
        "recommend": 0,
        "knowledge": 0,
    }

    def fake_router(
        query: str,
    ) -> RouterDecision:
        return RouterDecision(
            route="knowledge",
            routes=["knowledge"],
            reason="Real-estate knowledge question.",
        )

    def fake_search(state):
        calls["search"] += 1
        return "search"

    def fake_market(state):
        calls["market"] += 1
        return "market"

    def fake_recommend(state):
        calls["recommend"] += 1
        return "recommend"

    def fake_knowledge(state):
        calls["knowledge"] += 1
        return (
            "DOM means Days on Market."
        )

    orchestrator = build_orchestrator(
        router=fake_router,
        search_handler=fake_search,
        market_handler=fake_market,
        recommendation_handler=fake_recommend,
        knowledge_handler=fake_knowledge,
    )

    result = orchestrator.invoke(
        "What does DOM mean in real estate?"
    )

    assert result["route"] == "knowledge"

    assert result["agents_invoked"] == [
        "knowledge"
    ]

    assert result["knowledge_result"] == (
        "DOM means Days on Market."
    )

    assert result["final_response"] == (
        "DOM means Days on Market."
    )

    assert calls == {
        "search": 0,
        "market": 0,
        "recommend": 0,
        "knowledge": 1,
    }

def test_mixed_route_preserves_partial_result_on_failure():
    def fake_router(
        query: str,
    ) -> RouterDecision:
        return RouterDecision(
            route="mixed",
            routes=[
                "search",
                "market",
            ],
            reason=(
                "Query requests search and "
                "market analysis."
            ),
        )

    def fake_search(state):
        return {
            "listings": [
                "listing-1",
                "listing-2",
            ],
        }

    def failing_market(state):
        raise RuntimeError(
            "Market service unavailable"
        )

    orchestrator = build_orchestrator(
        router=fake_router,
        search_handler=fake_search,
        market_handler=failing_market,
    )

    result = orchestrator.invoke(
        (
            "Find homes in Pasadena and "
            "tell me whether prices are rising."
        )
    )

    assert result["route"] == "mixed"

    assert set(
        result["agents_invoked"]
    ) == {
        "search",
        "market",
    }

    assert result["search_result"] == {
        "listings": [
            "listing-1",
            "listing-2",
        ],
    }

    assert result["market_result"] is None

    assert len(
        result["errors"]
    ) == 1

    assert (
        "market: RuntimeError: "
        "Market service unavailable"
        in result["errors"][0]
    )

    assert (
        "Property Search:"
        in result["final_response"]
    )

    assert (
        "Partial errors:"
        in result["final_response"]
    )

    assert (
        "Market service unavailable"
        in result["final_response"]
    )