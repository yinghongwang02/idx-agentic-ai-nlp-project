from src.agents.intent_agent import IntentAgent
from src.memory.session_memory import SessionMemory


def main() -> None:
    memory = SessionMemory()
    agent = IntentAgent(memory=memory)

    queries = [
        (
            "Find 3 bedroom homes in Irvine "
            "with a garage, preferably with a pool."
        ),
        (
            "I would also prefer a view."
        ),
    ]

    for query in queries:
        intent = agent.run(query)

        print("=" * 80)
        print(f"Query: {query}")
        print(f"Keywords: {intent.keywords}")
        print(f"Preferences: {intent.preferences}")
        print(f"Memory: {memory.to_dict()}")


if __name__ == "__main__":
    main()