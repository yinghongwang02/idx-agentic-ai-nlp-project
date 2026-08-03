from src.workflow.graph import PropertySearchGraph
from src.agents.search_agent import SearchAgent
from src.search.mysql_search_repository import (
    MySQLSearchRepository,
)


def main() -> None:
    search_agent = SearchAgent(
        repository=MySQLSearchRepository(),
    )

    workflow = PropertySearchGraph(
        search_agent=search_agent,
        parallel_candidate_analysis=True,
        max_parallel_candidates=4,
    )

    result = workflow.run(
        "Find 3 bedroom homes in Irvine with a garage."
    )

    print(
        "Candidate errors:",
        result.get(
            "candidate_analysis_errors",
            [],
        ),
    )

    print(
        "Recommendation count:",
        len(
            result.get(
                "recommendations",
                [],
            )
        ),
    )


if __name__ == "__main__":
    main()