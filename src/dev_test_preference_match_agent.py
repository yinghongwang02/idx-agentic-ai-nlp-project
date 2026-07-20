from src.agents.preference_match_agent import PreferenceMatchAgent
from src.schemas.intent_schema import PropertyIntent
from src.search.mysql_search_repository import MySQLSearchRepository


def print_analysis(
    title,
    listing,
    intent,
    preference_agent,
):
    analysis = preference_agent.run(
        listing=listing,
        intent=intent,
    )

    print(f"\n{title}")
    print("-" * 100)
    print(
        f"Address: "
        f"{listing.unparsed_address}"
    )
    print(
        f"Preference Match Score: "
        f"{analysis.preference_match_score:.2f}"
    )
    print(
        f"Requested Preferences: "
        f"{analysis.requested_preferences}"
    )
    print(
        f"Matched Preferences: "
        f"{analysis.matched_preferences}"
    )
    print(
        f"Unmatched Preferences: "
        f"{analysis.unmatched_preferences}"
    )
    print("Signals:")

    for signal in analysis.signals:
        print(
            f"- {signal}"
        )

    return analysis


def run_controlled_score_tests(
    base_listing,
    intent,
    preference_agent,
):
    """
    Explicitly verify 100%, 50%, and 0%
    soft-preference match scenarios.

    The tests reuse one valid listing returned by MySQL and only
    replace public_remarks, so they stay compatible with the
    existing ListingSchema.
    """
    print(
        "\n"
        + "=" * 100
    )
    print(
        "CONTROLLED SOFT PREFERENCE SCORE TESTS"
    )
    print(
        "=" * 100
    )

    test_cases = [
        {
            "title": (
                "CASE 1 - EXPECTED 100% MATCH"
            ),
            "public_remarks": (
                "Beautiful home with a private pool "
                "and panoramic view."
            ),
            "expected_score": 100.0,
            "expected_matched": [
                "pool",
                "view",
            ],
            "expected_unmatched": [],
        },
        {
            "title": (
                "CASE 2 - EXPECTED 50% MATCH"
            ),
            "public_remarks": (
                "Beautiful home with a private pool "
                "and spacious backyard."
            ),
            "expected_score": 50.0,
            "expected_matched": [
                "pool",
            ],
            "expected_unmatched": [
                "view",
            ],
        },
        {
            "title": (
                "CASE 3 - EXPECTED 0% MATCH"
            ),
            "public_remarks": (
                "Updated home with a large garage "
                "and quiet backyard."
            ),
            "expected_score": 0.0,
            "expected_matched": [],
            "expected_unmatched": [
                "pool",
                "view",
            ],
        },
    ]

    for test_case in test_cases:
        test_listing = base_listing.model_copy(
            update={
                "public_remarks": (
                    test_case[
                        "public_remarks"
                    ]
                ),
            }
        )

        analysis = print_analysis(
            title=test_case["title"],
            listing=test_listing,
            intent=intent,
            preference_agent=preference_agent,
        )

        assert (
            analysis.preference_match_score
            == test_case["expected_score"]
        ), (
            f"{test_case['title']} failed: "
            f"expected score "
            f"{test_case['expected_score']}, "
            f"got "
            f"{analysis.preference_match_score}"
        )

        assert (
            analysis.matched_preferences
            == test_case["expected_matched"]
        ), (
            f"{test_case['title']} failed: "
            f"unexpected matched preferences "
            f"{analysis.matched_preferences}"
        )

        assert (
            analysis.unmatched_preferences
            == test_case["expected_unmatched"]
        ), (
            f"{test_case['title']} failed: "
            f"unexpected unmatched preferences "
            f"{analysis.unmatched_preferences}"
        )

        print(
            "PASS: score, matched preferences, "
            "and unmatched preferences are correct."
        )


def main() -> None:
    search_repository = (
        MySQLSearchRepository()
    )

    preference_agent = (
        PreferenceMatchAgent()
    )

    intent = PropertyIntent(
        city="Irvine",
        min_bedrooms=3,
        property_type=(
            "SingleFamilyResidence"
        ),
        keywords=[
            "garage",
        ],
        preferences=[
            "pool",
            "view",
        ],
    )

    listings = search_repository.search(
        intent=intent,
        limit=5,
    )

    if not listings:
        print(
            "No active listings found."
        )
        return

    run_controlled_score_tests(
        base_listing=listings[0],
        intent=intent,
        preference_agent=preference_agent,
    )

    print(
        "\n"
        + "=" * 100
    )
    print(
        "DATABASE SOFT PREFERENCE MATCH "
        "AGENT TEST"
    )
    print(
        "=" * 100
    )

    for index, listing in enumerate(
        listings,
        start=1,
    ):
        print_analysis(
            title=f"LISTING #{index}",
            listing=listing,
            intent=intent,
            preference_agent=preference_agent,
        )

    print(
        "\n"
        + "=" * 100
    )
    print(
        "SOFT PREFERENCE MATCH "
        "AGENT TEST COMPLETED"
    )
    print(
        "=" * 100
    )


if __name__ == "__main__":
    main()