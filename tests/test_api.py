from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.app import app, get_orchestrator


class FakeOrchestrator:
    def __init__(self) -> None:
        self.calls: list[
            dict[str, str | None]
        ] = []

    def invoke(
        self,
        user_query: str,
        *,
        session_id: str | None = None,
    ) -> dict:
        self.calls.append(
            {
                "user_query": user_query,
                "session_id": session_id,
            }
        )

        if (
            "similar to listing"
            in user_query.lower()
        ):
            return {
                "user_query": user_query,
                "session_id": session_id,
                "route": "recommend",
                "routes": ["recommend"],
                "route_reason": (
                    "Explicit similar-listing request."
                ),
                "agents_invoked": [
                    "recommend"
                ],
                "recommendation_result": [
                    {
                        "listing_id": "TEST-002",
                    }
                ],
                "final_response": (
                    "Similar-home recommendations."
                ),
                "errors": [],
            }

        if (
            "prices are rising"
            in user_query.lower()
            and "find homes"
            in user_query.lower()
        ):
            return {
                "user_query": user_query,
                "session_id": session_id,
                "route": "mixed",
                "routes": [
                    "search",
                    "market",
                ],
                "route_reason": (
                    "Search and market request."
                ),
                "agents_invoked": [
                    "search",
                    "market",
                ],
                "final_response": (
                    "Property Search:\n"
                    "Found homes.\n\n"
                    "Market Analysis:\n"
                    "Prices are rising."
                ),
                "errors": [],
            }

        if "dom" in user_query.lower():
            return {
                "user_query": user_query,
                "session_id": session_id,
                "route": "knowledge",
                "routes": ["knowledge"],
                "route_reason": (
                    "Knowledge question."
                ),
                "agents_invoked": [
                    "knowledge"
                ],
                "final_response": (
                    "DOM means Days on Market."
                ),
                "errors": [],
            }

        return {
            "user_query": user_query,
            "session_id": session_id,
            "route": "search",
            "routes": ["search"],
            "route_reason": (
                "Property search request."
            ),
            "agents_invoked": [
                "search"
            ],
            "final_response": (
                "Found 5 homes in Irvine."
            ),
            "errors": [],
        }


def make_client():
    fake_orchestrator = (
        FakeOrchestrator()
    )

    app.dependency_overrides[
        get_orchestrator
    ] = lambda: fake_orchestrator

    client = TestClient(app)

    return (
        client,
        fake_orchestrator,
    )


def teardown_function():
    app.dependency_overrides.clear()


def test_health_endpoint():
    client, _ = make_client()

    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"

    assert "environment" in data


def test_search_endpoint():
    client, orchestrator = (
        make_client()
    )

    response = client.post(
        "/search",
        json={
            "query": (
                "Find homes in Irvine."
            ),
            "session_id": (
                "session-search"
            ),
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["route"] == "search"

    assert data["routes"] == [
        "search"
    ]

    assert data[
        "agents_invoked"
    ] == [
        "search"
    ]

    assert data[
        "final_response"
    ] == (
        "Found 5 homes in Irvine."
    )

    assert data["errors"] == []

    assert data["session_id"] == (
        "session-search"
    )

    assert orchestrator.calls == [
        {
            "user_query": (
                "Find homes in Irvine."
            ),
            "session_id": (
                "session-search"
            ),
        }
    ]


def test_recommend_endpoint_builds_query():
    client, orchestrator = (
        make_client()
    )

    response = client.post(
        "/recommend",
        json={
            "listing_id": (
                "TEST-001"
            ),
            "session_id": (
                "session-recommend"
            ),
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["route"] == (
        "recommend"
    )

    assert data["routes"] == [
        "recommend"
    ]

    assert data[
        "agents_invoked"
    ] == [
        "recommend"
    ]

    assert orchestrator.calls == [
        {
            "user_query": (
                "Show me homes similar "
                "to listing TEST-001."
            ),
            "session_id": (
                "session-recommend"
            ),
        }
    ]


def test_chat_endpoint_routes_knowledge():
    client, _ = make_client()

    response = client.post(
        "/chat",
        json={
            "query": (
                "What does DOM mean?"
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["route"] == (
        "knowledge"
    )

    assert data["routes"] == [
        "knowledge"
    ]

    assert data[
        "final_response"
    ] == (
        "DOM means Days on Market."
    )


def test_chat_endpoint_routes_mixed():
    client, _ = make_client()

    response = client.post(
        "/chat",
        json={
            "query": (
                "Find homes in Irvine "
                "and tell me whether "
                "prices are rising."
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["route"] == "mixed"

    assert set(
        data["routes"]
    ) == {
        "search",
        "market",
    }

    assert set(
        data["agents_invoked"]
    ) == {
        "search",
        "market",
    }

    assert (
        "Property Search:"
        in data["final_response"]
    )

    assert (
        "Market Analysis:"
        in data["final_response"]
    )


def test_search_rejects_empty_query():
    client, _ = make_client()

    response = client.post(
        "/search",
        json={
            "query": "   ",
        },
    )

    assert response.status_code == 422


def test_recommend_rejects_empty_listing_id():
    client, _ = make_client()

    response = client.post(
        "/recommend",
        json={
            "listing_id": "   ",
        },
    )

    assert response.status_code == 422


def test_chat_logs_success(
    caplog,
):
    client, _ = make_client()

    with caplog.at_level(
        "INFO",
        logger="idx.api",
    ):
        response = client.post(
            "/chat",
            json={
                "query": (
                    "What does DOM mean?"
                ),
                "session_id": (
                    "logging-test"
                ),
            },
        )

    assert response.status_code == 200

    assert (
        "orchestration_completed"
        in caplog.text
    )

    assert (
        "route=knowledge"
        in caplog.text
    )

    assert (
        "agents=knowledge"
        in caplog.text
    )

    assert (
        "errors=0"
        in caplog.text
    )

    assert (
        "session_id=logging-test"
        in caplog.text
    )


def test_chat_logs_partial_failure_warning(
    caplog,
):
    class PartialFailureOrchestrator:
        def invoke(
            self,
            user_query: str,
            *,
            session_id: str | None = None,
        ) -> dict:
            return {
                "user_query": user_query,
                "session_id": session_id,
                "route": "mixed",
                "routes": [
                    "search",
                    "market",
                ],
                "route_reason": (
                    "Search and market request."
                ),
                "agents_invoked": [
                    "search",
                    "market",
                ],
                "final_response": (
                    "Property Search:\n"
                    "Found homes.\n\n"
                    "Partial errors:\n"
                    "- market failed"
                ),
                "errors": [
                    "market: RuntimeError: failed"
                ],
            }

    app.dependency_overrides[
        get_orchestrator
    ] = lambda: (
        PartialFailureOrchestrator()
    )

    client = TestClient(app)

    with caplog.at_level(
        "WARNING",
        logger="idx.api",
    ):
        response = client.post(
            "/chat",
            json={
                "query": (
                    "Find homes and analyze "
                    "the market."
                )
            },
        )

    assert response.status_code == 200

    assert response.json()[
        "errors"
    ] == [
        "market: RuntimeError: failed"
    ]

    assert (
        "orchestration_completed"
        in caplog.text
    )

    assert (
        "route=mixed"
        in caplog.text
    )

    assert (
        "errors=1"
        in caplog.text
    )

    warning_records = [
        record
        for record in caplog.records
        if record.name == "idx.api"
        and record.levelname == "WARNING"
    ]

    assert warning_records