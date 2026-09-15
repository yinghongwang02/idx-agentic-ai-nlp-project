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

def test_intent_agent_parses_multiple_soft_preferences():
    agent = IntentAgent()

    intent = agent.run(
        "Find 3 bedroom homes in Irvine with a garage, "
        "preferably with a pool and a view."
    )

    assert intent.keywords == ["garage"]
    assert intent.preferences == ["pool", "view"]


def test_intent_agent_keeps_non_preferred_features_as_keywords():
    agent = IntentAgent()

    intent = agent.run(
        "Find homes in Irvine with a garage and a pool"
    )

    assert "garage" in intent.keywords
    assert "pool" in intent.keywords
    assert intent.preferences == []


def test_intent_agent_parses_single_soft_preference():
    agent = IntentAgent()

    intent = agent.run(
        "Find homes in Irvine with a garage, "
        "preferably with a pool"
    )

    assert intent.keywords == ["garage"]
    assert intent.preferences == ["pool"]


def test_intent_agent_parses_decimal_million_price_with_period():
    agent = IntentAgent()

    intent = agent.run(
        "Find homes in Irvine under $1.5M."
    )

    assert intent.max_price == 1500000


def test_intent_agent_parses_common_price_budget_formats():
    agent = IntentAgent()

    cases = [
        ("Find homes under $1.7M.", 1700000),
        ("Find homes under $900K.", 900000),
        ("Find homes under $1,500,000.", 1500000),
        ("Find homes under 1.5 million.", 1500000),
    ]

    for query, expected_price in cases:
        intent = agent.run(query)

        assert intent.max_price == expected_price


def test_generic_homes_does_not_imply_single_family():
    agent = IntentAgent()

    intent = agent.run(
        "Find homes in Irvine under $1.5M."
    )

    assert intent.property_type is None


def test_explicit_single_family_still_parses_correctly():
    agent = IntentAgent()

    intent = agent.run(
        "Find single family homes in Irvine under $1.5M."
    )

    assert intent.property_type == "SingleFamilyResidence"
    assert intent.max_price == 1500000