from src.orchestration.router import IntentRouter


def main() -> None:
    router = IntentRouter()

    cases = [
        (
            "Find 3-bedroom homes under $900k in Irvine.",
            "search",
        ),
        (
            "What is the housing market like in Pasadena?",
            "market",
        ),
        (
            "Are home prices rising in Pasadena?",
            "market",
        ),
        (
            "Show me homes similar to this listing.",
            "recommend",
        ),
        (
            "Find similar homes to listing ABC123.",
            "recommend",
        ),
        (
            "What does DaysOnMarket mean?",
            "knowledge",
        ),
        (
            "Define ClosePrice.",
            "knowledge",
        ),
        (
            "Find affordable homes in Pasadena and "
            "tell me whether prices are rising.",
            "mixed",
        ),
    ]

    print("=" * 80)
    print("ROUTER SMOKE TEST")
    print("=" * 80)

    passed = 0

    for query, expected in cases:
        decision = router.route(
            query
        )

        correct = (
            decision.route == expected
        )

        if correct:
            passed += 1

        print()
        print("Query:")
        print(query)

        print(
            "Expected:",
            expected,
        )

        print(
            "Actual:",
            decision.route,
        )

        print(
            "Routes:",
            decision.routes,
        )

        print(
            "Reason:",
            decision.reason,
        )

        print(
            "Result:",
            "PASS" if correct else "FAIL",
        )

    print()
    print("=" * 80)
    print(
        f"Passed: {passed}/{len(cases)}"
    )
    print("=" * 80)

    assert passed == len(cases)


if __name__ == "__main__":
    main()