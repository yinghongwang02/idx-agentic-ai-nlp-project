from src.agents.intent_agent import IntentAgent
from src.memory.session_memory import SessionMemory


def test_follow_up_queries_inherit_session_preferences() -> None:
    memory = SessionMemory()
    agent = IntentAgent(memory=memory)

    first_intent = agent.run(
        "Find townhouses in Irvine"
    )

    assert first_intent.city == "Irvine"
    assert first_intent.property_type == "Townhouse"

    second_intent = agent.run(
        "Under 1.2 million"
    )

    assert second_intent.city == "Irvine"
    assert second_intent.property_type == "Townhouse"
    assert second_intent.max_price == 1_200_000

    third_intent = agent.run(
        "At least 3 bedrooms with a garage"
    )

    assert third_intent.city == "Irvine"
    assert third_intent.property_type == "Townhouse"
    assert third_intent.max_price == 1_200_000
    assert third_intent.min_bedrooms == 3
    assert third_intent.keywords == ["garage"]


def test_keywords_accumulate_across_turns() -> None:
    memory = SessionMemory()
    agent = IntentAgent(memory=memory)

    agent.run("Find homes with a garage")
    intent = agent.run("Also include a pool")

    assert intent.keywords == ["garage", "pool"]


def test_clear_starts_a_new_search_session() -> None:
    memory = SessionMemory()
    agent = IntentAgent(memory=memory)

    agent.run(
        "Find townhouses in Irvine under 1.2 million"
    )

    memory.clear()

    new_intent = agent.run(
        "Show me condos in Pasadena"
    )

    assert new_intent.city == "Pasadena"
    assert new_intent.property_type == "Condominium"
    assert new_intent.max_price is None
    assert new_intent.min_bedrooms is None
    assert new_intent.keywords == []


def test_intent_agent_still_works_without_memory() -> None:
    agent = IntentAgent()

    intent = agent.run(
        "Find 3 bedroom condos in Irvine under 900k"
    )

    assert intent.city == "Irvine"
    assert intent.max_price == 900_000
    assert intent.min_bedrooms == 3
    assert intent.property_type == "Condominium"