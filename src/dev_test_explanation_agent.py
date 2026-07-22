from src.agents.search_agent import SearchAgent
from src.search.mysql_search_repository import MySQLSearchRepository
from src.workflow.graph import PropertySearchGraph


def main() -> None:
    repository = MySQLSearchRepository()

    search_agent = SearchAgent(
        repository=repository,
    )

    graph = PropertySearchGraph(
        search_agent=search_agent,
    )

    query = (
        "Find 3 bedroom homes in Irvine with a garage, "
        "preferably with a pool and a view."
    )

    print("=" * 100)
    print("EXPLANATION AGENT END-TO-END REVIEW")
    print("=" * 100)
    print(f"Query: {query}")

    state = graph.run(query)

    if state.get("error"):
        print("\nERROR")
        print("-" * 100)
        print(state["error"])
        return

    if state.get("blocked"):
        print("\nREQUEST BLOCKED")
        print("-" * 100)
        print(state.get("final_response", ""))
        return

    intent = state.get("intent")
    recommendations = state.get(
        "recommendations",
        [],
    )

    print("\n" + "=" * 100)
    print("PARSED INTENT")
    print("=" * 100)

    if intent is not None:
        print(
            intent.model_dump()
        )

    print("\n" + "=" * 100)
    print("STRUCTURED TOP 5 RECOMMENDATIONS")
    print("=" * 100)

    if not recommendations:
        print(
            "No recommendations returned."
        )
    else:
        for rank, recommendation in enumerate(
            recommendations,
            start=1,
        ):
            listing = recommendation.listing

            print(f"\nRANK #{rank}")
            print("-" * 100)
            print(
                f"Address: "
                f"{listing.unparsed_address}"
            )

            if listing.list_price is not None:
                print(
                    f"Price: "
                    f"${listing.list_price:,.0f}"
                )
            else:
                print(
                    "Price: N/A"
                )

            print(
                f"Overall Score: "
                f"{recommendation.overall_score:.2f}"
            )
            print(
                f"Preference Match: "
                f"{recommendation.preference_match_score:.2f}"
            )
            print(
                f"Comparable Value: "
                f"{recommendation.comparable_value_score:.2f}"
            )
            print(
                f"Negotiation: "
                f"{recommendation.negotiation_score:.2f}"
            )
            print(
                f"Label: "
                f"{recommendation.recommendation_label}"
            )

            print(
                "Recommendation Reasons:"
            )

            if recommendation.reasons:
                for reason in recommendation.reasons:
                    print(
                        f"- {reason}"
                    )
            else:
                print(
                    "- No recommendation reasons."
                )

    print("\n" + "=" * 100)
    print("EXPLANATION AGENT OUTPUT")
    print("=" * 100)
    print(
        state.get(
            "explanation",
            "",
        )
    )

    print("\n" + "=" * 100)
    print("FINAL RESPONSE AFTER OUTPUT COMPLIANCE")
    print("=" * 100)
    print(
        state.get(
            "final_response",
            "",
        )
    )

    print("\n" + "=" * 100)
    print("MANUAL REVIEW CHECKLIST")
    print("=" * 100)
    print(
        "1. Does the explanation preserve the same Top 5 ranking?"
    )
    print(
        "2. Do the displayed scores match the structured recommendation scores?"
    )
    print(
        "3. Do the reasons support each listing's actual score profile?"
    )
    print(
        "4. Are soft preferences described accurately?"
    )
    print(
        "5. Are comparable-value and negotiation signals understandable?"
    )
    print(
        "6. Is the wording concise enough for the Streamlit UI?"
    )
    print(
        "7. Does final_response match explanation when compliance is green?"
    )

    print("\n" + "=" * 100)
    print(
        "EXPLANATION AGENT REVIEW COMPLETED"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()