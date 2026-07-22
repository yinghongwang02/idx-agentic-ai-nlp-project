from src.agents.preference_match_agent import PreferenceMatchAgent
from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema


def make_listing(
    remarks: str,
) -> ListingSchema:
    return ListingSchema(
        listing_key="TEST-001",
        unparsed_address="1 Test Street",
        city="Irvine",
        list_price=1_000_000,
        public_remarks=remarks,
    )


def make_intent() -> PropertyIntent:
    return PropertyIntent(
        city="Irvine",
        preferences=[
            "pool",
            "view",
        ],
    )


def test_preference_match_agent_returns_100_for_full_match() -> None:
    agent = PreferenceMatchAgent()

    analysis = agent.run(
        listing=make_listing(
            "Beautiful home with a private pool "
            "and panoramic view."
        ),
        intent=make_intent(),
    )

    assert analysis.preference_match_score == 100.0
    assert analysis.requested_preferences == [
        "pool",
        "view",
    ]
    assert analysis.matched_preferences == [
        "pool",
        "view",
    ]
    assert analysis.unmatched_preferences == []


def test_preference_match_agent_returns_50_for_partial_match() -> None:
    agent = PreferenceMatchAgent()

    analysis = agent.run(
        listing=make_listing(
            "Beautiful home with a private pool "
            "and spacious backyard."
        ),
        intent=make_intent(),
    )

    assert analysis.preference_match_score == 50.0
    assert analysis.matched_preferences == [
        "pool",
    ]
    assert analysis.unmatched_preferences == [
        "view",
    ]


def test_preference_match_agent_returns_0_for_no_match() -> None:
    agent = PreferenceMatchAgent()

    analysis = agent.run(
        listing=make_listing(
            "Updated home with a large garage "
            "and quiet backyard."
        ),
        intent=make_intent(),
    )

    assert analysis.preference_match_score == 0.0
    assert analysis.matched_preferences == []
    assert analysis.unmatched_preferences == [
        "pool",
        "view",
    ]


def test_preference_match_agent_uses_neutral_score_without_preferences() -> None:
    agent = PreferenceMatchAgent()

    analysis = agent.run(
        listing=make_listing(
            "Beautiful home with a private pool "
            "and panoramic view."
        ),
        intent=PropertyIntent(
            city="Irvine",
            preferences=[],
        ),
    )

    assert analysis.preference_match_score == 50.0
    assert analysis.requested_preferences == []
    assert analysis.matched_preferences == []
    assert analysis.unmatched_preferences == []


def test_preference_match_agent_is_case_insensitive() -> None:
    agent = PreferenceMatchAgent()

    analysis = agent.run(
        listing=make_listing(
            "This property includes a PRIVATE POOL "
            "and a PANORAMIC VIEW."
        ),
        intent=make_intent(),
    )

    assert analysis.preference_match_score == 100.0
    assert analysis.matched_preferences == [
        "pool",
        "view",
    ]