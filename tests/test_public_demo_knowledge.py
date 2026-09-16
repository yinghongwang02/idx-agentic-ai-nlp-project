from src.public_demo.public_composition import (
    create_public_orchestrator,
)


def test_public_demo_knowledge_routes_correctly():
    orchestrator = create_public_orchestrator()

    result = orchestrator.invoke(
        "What does DOM mean in real estate?"
    )

    assert result["route"] == "knowledge"
    assert result["agents_invoked"] == ["knowledge"]
    assert result["errors"] == []


def test_public_demo_knowledge_answers_dom_question():
    orchestrator = create_public_orchestrator()

    result = orchestrator.invoke(
        "What does DOM mean in real estate?"
    )

    response = result["final_response"].lower()

    assert "days on market" in response
    assert result["errors"] == []


def test_public_demo_knowledge_answers_comparable_sales_question():
    orchestrator = create_public_orchestrator()

    result = orchestrator.invoke(
        "How are comparable sales used?"
    )

    response = result["final_response"].lower()

    assert "comparable" in response
    assert "reference" in response
    assert result["errors"] == []