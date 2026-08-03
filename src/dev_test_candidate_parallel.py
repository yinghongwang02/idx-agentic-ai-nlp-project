from time import perf_counter

from src.agents.search_agent import SearchAgent
from src.search.mysql_search_repository import (
    MySQLSearchRepository,
)
from src.workflow.graph import PropertySearchGraph


def main() -> None:
    search_agent = SearchAgent(
        repository=MySQLSearchRepository(),
    )

    workflow = PropertySearchGraph(
        search_agent=search_agent,
        parallel_candidate_analysis=True,
        max_parallel_candidates=4,
    )

    query = (
        "Find 3 bedroom homes in Irvine with a garage."
    )

    started_at = perf_counter()

    result = workflow.run(query)

    elapsed_seconds = perf_counter() - started_at

    candidate_errors = result.get(
        "candidate_analysis_errors",
        [],
    )

    recommendations = result.get(
        "recommendations",
        [],
    )

    search_results = result.get(
        "search_results",
        [],
    )

    print("=" * 80)
    print("CANDIDATE-LEVEL PARALLEL SMOKE TEST")
    print("=" * 80)
    print(f"Query: {query}")
    print(
        "Parallel enabled:",
        workflow.parallel_candidate_analysis,
    )
    print(
        "Max parallel candidates:",
        workflow.max_parallel_candidates,
    )
    print(
        "Candidate count:",
        len(search_results),
    )
    print(
        "Recommendation count:",
        len(recommendations),
    )
    print(
        "Candidate errors:",
        candidate_errors,
    )
    print(
        f"Runtime: {elapsed_seconds:.2f} seconds"
    )

    if result.get("error") is not None:
        raise AssertionError(
            f"Workflow error: {result['error']}"
        )

    assert workflow.parallel_candidate_analysis
    assert workflow.max_parallel_candidates == 4
    assert search_results
    assert recommendations
    assert (
        len(recommendations)
        <= workflow.RECOMMENDATION_LIMIT
    )
    assert candidate_errors == []

    print("\nTop recommendations:")

    for rank, recommendation in enumerate(
        recommendations,
        start=1,
    ):
        print(
            f"{rank}. "
            f"{recommendation.listing.listing_key} | "
            f"{recommendation.overall_score:.2f}"
        )

    print(
        "\nCandidate-level parallel smoke test: PASS"
    )


if __name__ == "__main__":
    main()