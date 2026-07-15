from typing import Any

from src.memory.session_memory import SessionMemory
from src.workflow.mock_workflow import PropertySearchWorkflow


class FakeSearchAgent:
    def run(self, intent: Any) -> list[dict[str, Any]]:
        return [
            {
                "listing_key": "TEST-001",
                "city": intent.city,
                "list_price": 900_000,
            }
        ]


class FakeRecommendationAgent:
    def run(
        self,
        listings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return listings


class FakeExplanationAgent:
    def run(
        self,
        intent: Any,
        listings: list[dict[str, Any]],
    ) -> str:
        if not listings:
            return "No matching properties were found."

        return (
            f"Found {len(listings)} matching property based on "
            f"your objective search preferences in {intent.city}."
        )


def print_state(
    title: str,
    state: dict[str, Any],
) -> None:
    print("=" * 90)
    print(title)
    print("Blocked:", state.get("blocked"))
    print("Intent:", state.get("intent"))
    print("Memory:", state.get("memory_snapshot"))
    print("Query compliance:", state.get("query_compliance"))
    print("Output compliance:", state.get("output_compliance"))
    print("Final response:", state.get("final_response"))
    print("Error:", state.get("error"))


def main() -> None:
    memory = SessionMemory()

    workflow = PropertySearchWorkflow(
        search_agent=FakeSearchAgent(),
        memory=memory,
        recommendation_agent=FakeRecommendationAgent(),
        explanation_agent=FakeExplanationAgent(),
    )

    state_1 = workflow.run(
        "Find townhouses in Irvine"
    )
    print_state("Turn 1", state_1)

    state_2 = workflow.run(
        "Under 1.2 million with a garage"
    )
    print_state("Turn 2", state_2)

    blocked_state = workflow.run(
        "Show me homes in a Christian neighborhood."
    )
    print_state("Blocked request", blocked_state)

    print("=" * 90)
    print("Memory after blocked request:")
    print(workflow.get_memory_snapshot())

    workflow.clear_session()

    print("=" * 90)
    print("Memory after clear:")
    print(workflow.get_memory_snapshot())


if __name__ == "__main__":
    main()