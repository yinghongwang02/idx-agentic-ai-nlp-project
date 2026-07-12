from src.agents.intent_agent import IntentAgent
from src.memory.session_memory import SessionMemory


def print_turn(
    turn_number: int,
    query: str,
    agent: IntentAgent,
    memory: SessionMemory,
) -> None:
    intent = agent.run(query)

    print("=" * 80)
    print(f"Turn {turn_number}: {query}")
    print("Returned intent:")
    print(intent.model_dump())
    print("Memory snapshot:")
    print(memory.to_dict())


def main() -> None:
    memory = SessionMemory()
    agent = IntentAgent(memory=memory)

    print_turn(
        turn_number=1,
        query="Find townhouses in Irvine",
        agent=agent,
        memory=memory,
    )

    print_turn(
        turn_number=2,
        query="Under 1.2 million",
        agent=agent,
        memory=memory,
    )

    print_turn(
        turn_number=3,
        query="At least 3 bedrooms with a garage",
        agent=agent,
        memory=memory,
    )

    print_turn(
        turn_number=4,
        query="Also include a pool",
        agent=agent,
        memory=memory,
    )

    print("=" * 80)
    print("Start a new search session")
    memory.clear()

    print_turn(
        turn_number=5,
        query="Show me condos in Pasadena",
        agent=agent,
        memory=memory,
    )


if __name__ == "__main__":
    main()