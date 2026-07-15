from src.agents.intent_agent import IntentAgent


def test_intent_agent_parses_basic_property_query():
    agent = IntentAgent()

    intent = agent.run(
        "Show me 3 bedroom condos in Irvine under 900k with pool"
    )

    assert intent.city == "Irvine"
    assert intent.max_price == 900000
    assert intent.min_bedrooms == 3
    assert intent.property_type == "Condominium"
    assert "pool" in intent.keywords


def test_intent_agent_parses_million_price_suffix():
    agent = IntentAgent()

    intent = agent.run(
        "Find single family homes in Pasadena below 1.2m"
    )

    assert intent.city == "Pasadena"
    assert intent.max_price == 1200000
    assert intent.property_type == "SingleFamilyResidence"


def test_intent_agent_extracts_multiple_keywords():
    agent = IntentAgent()

    intent = agent.run(
        "Find homes in Newport Beach with ocean view, remodeled kitchen, and garage"
    )

    assert intent.city == "Newport Beach"
    assert "ocean view" in intent.keywords
    assert "remodeled" in intent.keywords
    assert "garage" in intent.keywords