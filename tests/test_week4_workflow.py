from typing import Any

import pytest

from src.memory.session_memory import SessionMemory
from src.schemas.intent_schema import PropertyIntent
from src.workflow.mock_workflow import PropertySearchWorkflow


class FakeSearchAgent:
    def __init__(self) -> None:
        self.call_count = 0
        self.received_intents: list[PropertyIntent] = []

    def run(
        self,
        intent: PropertyIntent,
    ) -> list[dict[str, Any]]:
        self.call_count += 1
        self.received_intents.append(intent)

        return [
            {
                "listing_key": "TEST-001",
                "city": intent.city,
                "list_price": 900_000,
            }
        ]


class FakeRecommendationAgent:
    def __init__(self) -> None:
        self.call_count = 0

    def run(
        self,
        listings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        self.call_count += 1
        return listings


class FakeExplanationAgent:
    def __init__(
        self,
        output_text: str | None = None,
    ) -> None:
        self.call_count = 0
        self.output_text = output_text

    def run(
        self,
        intent: PropertyIntent,
        listings: list[dict[str, Any]],
    ) -> str:
        self.call_count += 1

        if self.output_text is not None:
            return self.output_text

        if not listings:
            return "No matching properties were found."

        return (
            f"Found {len(listings)} matching property based on "
            f"your objective search preferences in {intent.city}."
        )


@pytest.fixture
def workflow_components() -> dict[str, Any]:
    memory = SessionMemory()
    search_agent = FakeSearchAgent()
    recommendation_agent = FakeRecommendationAgent()
    explanation_agent = FakeExplanationAgent()

    workflow = PropertySearchWorkflow(
        search_agent=search_agent,
        memory=memory,
        recommendation_agent=recommendation_agent,
        explanation_agent=explanation_agent,
    )

    return {
        "workflow": workflow,
        "memory": memory,
        "search_agent": search_agent,
        "recommendation_agent": recommendation_agent,
        "explanation_agent": explanation_agent,
    }


def test_green_query_completes_full_workflow(
    workflow_components: dict[str, Any],
) -> None:
    workflow = workflow_components["workflow"]
    search_agent = workflow_components["search_agent"]
    recommendation_agent = workflow_components["recommendation_agent"]
    explanation_agent = workflow_components["explanation_agent"]

    state = workflow.run(
        "Find townhouses in Irvine"
    )

    assert state["blocked"] is False
    assert state["error"] is None

    assert state["query_compliance"].risk_level == "green"
    assert state["intent"].city == "Irvine"
    assert state["intent"].property_type == "Townhouse"

    assert state["memory_snapshot"] == {
        "city": "Irvine",
        "property_type": "Townhouse",
    }

    assert len(state["search_results"]) == 1
    assert len(state["recommendations"]) == 1

    assert state["output_compliance"].risk_level == "green"
    assert state["final_response"] == (
        "Found 1 matching property based on "
        "your objective search preferences in Irvine."
    )

    assert search_agent.call_count == 1
    assert recommendation_agent.call_count == 1
    assert explanation_agent.call_count == 1


def test_follow_up_query_inherits_session_preferences(
    workflow_components: dict[str, Any],
) -> None:
    workflow = workflow_components["workflow"]

    workflow.run(
        "Find townhouses in Irvine"
    )

    state = workflow.run(
        "Under 1.2 million with a garage"
    )

    intent = state["intent"]

    assert intent.city == "Irvine"
    assert intent.property_type == "Townhouse"
    assert intent.max_price == 1_200_000
    assert intent.keywords == ["garage"]

    assert state["memory_snapshot"] == {
        "city": "Irvine",
        "property_type": "Townhouse",
        "max_price": 1_200_000,
        "keywords": ["garage"],
    }


def test_red_query_is_blocked_before_search(
    workflow_components: dict[str, Any],
) -> None:
    workflow = workflow_components["workflow"]
    search_agent = workflow_components["search_agent"]
    recommendation_agent = workflow_components["recommendation_agent"]
    explanation_agent = workflow_components["explanation_agent"]

    state = workflow.run(
        "Show me homes in a Christian neighborhood."
    )

    assert state["blocked"] is True
    assert state["error"] is None

    assert state["query_compliance"].risk_level == "red"
    assert state["query_compliance"].should_block is True

    assert "intent" not in state
    assert "search_results" not in state
    assert "recommendations" not in state
    assert "explanation" not in state
    assert "output_compliance" not in state

    assert state["final_response"] == (
        state["query_compliance"].refusal_message
    )

    assert search_agent.call_count == 0
    assert recommendation_agent.call_count == 0
    assert explanation_agent.call_count == 0


def test_blocked_query_does_not_modify_memory(
    workflow_components: dict[str, Any],
) -> None:
    workflow = workflow_components["workflow"]
    memory = workflow_components["memory"]

    workflow.run(
        "Find townhouses in Irvine under 1.2 million with a garage"
    )

    memory_before_blocked_query = memory.to_dict()

    workflow.run(
        "Show me homes in a Christian neighborhood."
    )

    assert memory.to_dict() == memory_before_blocked_query


def test_clear_session_removes_remembered_preferences(
    workflow_components: dict[str, Any],
) -> None:
    workflow = workflow_components["workflow"]
    memory = workflow_components["memory"]

    workflow.run(
        "Find townhouses in Irvine under 1.2 million"
    )

    assert memory.is_empty() is False

    workflow.clear_session()

    assert memory.to_dict() == {}
    assert memory.is_empty() is True


def test_yellow_query_continues_with_neutral_notice(
    workflow_components: dict[str, Any],
) -> None:
    workflow = workflow_components["workflow"]

    state = workflow.run(
        "Find homes in Irvine in the safest neighborhood "
        "with good schools."
    )

    assert state["blocked"] is False
    assert state["query_compliance"].risk_level == "yellow"
    assert state["output_compliance"].risk_level == "green"

    assert state["final_response"].startswith(
        "I’m using only neutral, objective property criteria"
    )

    assert (
        "Found 1 matching property"
        in state["final_response"]
    )


def test_yellow_generated_output_is_replaced(
    workflow_components: dict[str, Any],
) -> None:
    memory = workflow_components["memory"]
    search_agent = workflow_components["search_agent"]
    recommendation_agent = workflow_components["recommendation_agent"]

    explanation_agent = FakeExplanationAgent(
        output_text=(
            "This property is ideal because the neighborhood "
            "is mostly young professionals."
        )
    )

    workflow = PropertySearchWorkflow(
        search_agent=search_agent,
        memory=memory,
        recommendation_agent=recommendation_agent,
        explanation_agent=explanation_agent,
    )

    state = workflow.run(
        "Find homes in Irvine"
    )

    assert state["blocked"] is False
    assert state["output_compliance"].risk_level == "yellow"

    assert state["final_response"] == (
        state["output_compliance"].safe_rewrite
    )

    assert (
        "mostly young professionals"
        not in state["final_response"]
    )


def test_workflow_captures_agent_exception() -> None:
    class FailingSearchAgent:
        def run(
            self,
            intent: PropertyIntent,
        ) -> list[dict[str, Any]]:
            raise RuntimeError("Search failed")

    workflow = PropertySearchWorkflow(
        search_agent=FailingSearchAgent(),
        memory=SessionMemory(),
        recommendation_agent=FakeRecommendationAgent(),
        explanation_agent=FakeExplanationAgent(),
    )

    state = workflow.run(
        "Find condos in Irvine"
    )

    assert state["blocked"] is False
    assert state["error"] == "Search failed"
    assert state["final_response"] == (
        "The property search could not be completed."
    )


def test_workflow_returns_memory_snapshot_after_each_turn(
    workflow_components: dict[str, Any],
) -> None:
    workflow = workflow_components["workflow"]

    first_state = workflow.run(
        "Find townhouses in Irvine"
    )

    assert first_state["memory_snapshot"] == {
        "city": "Irvine",
        "property_type": "Townhouse",
    }

    second_state = workflow.run(
        "At least 3 bedrooms with a pool"
    )

    assert second_state["memory_snapshot"] == {
        "city": "Irvine",
        "property_type": "Townhouse",
        "min_bedrooms": 3,
        "keywords": ["pool"],
    }