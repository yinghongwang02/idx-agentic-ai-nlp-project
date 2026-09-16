from src.public_demo.public_composition import (
    create_public_orchestrator,
)


def test_public_demo_recommendation_routes_correctly():
    orchestrator = create_public_orchestrator()

    result = orchestrator.invoke(
        "Show me homes similar to listing DEMO-001"
    )

    assert result["route"] == "recommend"
    assert result["agents_invoked"] == ["recommend"]
    assert result["errors"] == []


def test_public_demo_recommendation_excludes_target_listing():
    orchestrator = create_public_orchestrator()

    result = orchestrator.invoke(
        "Show me homes similar to listing DEMO-001"
    )

    response = result["final_response"]

    assert "DEMO-001" not in response
    assert "128 Demo Oak Drive" not in response


def test_public_demo_condo_recommendation_returns_results():
    orchestrator = create_public_orchestrator()

    result = orchestrator.invoke(
        "Find similar homes to listing id DEMO-004"
    )

    response = result["final_response"]

    assert result["route"] == "recommend"
    assert result["errors"] == []
    assert "Similar-home recommendations:" in response
    assert "DEMO-004" not in response