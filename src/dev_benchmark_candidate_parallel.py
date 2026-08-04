from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Callable

from src.agents.search_agent import SearchAgent
from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema
from src.schemas.recommendation_score_schema import (
    RecommendationScore,
)
from src.search.mysql_search_repository import (
    MySQLSearchRepository,
)
from src.workflow.graph import PropertySearchGraph


QUERY = (
    "Find 3 bedroom homes in Irvine with a garage, "
    "preferably with a pool."
)

RUNS_PER_MODE = 3
MAX_PARALLEL_CANDIDATES = 4

OUTPUT_DIRECTORY = Path(
    "artifacts/benchmarks"
)


@dataclass(frozen=True)
class BenchmarkRun:
    mode: str
    run_number: int
    elapsed_seconds: float
    candidate_count: int
    successful_count: int
    error_count: int


def recommendation_signature(
    recommendation: RecommendationScore,
) -> tuple:
    """
    Return a deterministic representation for consistency checks.
    """
    return (
        recommendation.listing.listing_key,
        round(
            recommendation.overall_score,
            6,
        ),
        round(
            recommendation.preference_match_score,
            6,
        ),
        round(
            recommendation.comparable_value_score,
            6,
        ),
        round(
            recommendation.negotiation_score,
            6,
        ),
        recommendation.recommendation_label,
        tuple(recommendation.reasons),
    )


def ranked_signatures(
    workflow: PropertySearchGraph,
    recommendations: list[RecommendationScore],
) -> list[tuple]:
    ranked = workflow.recommendation_agent.rank(
        recommendations=recommendations,
        limit=workflow.RECOMMENDATION_LIMIT,
    )

    return [
        recommendation_signature(
            recommendation
        )
        for recommendation in ranked
    ]


def run_analysis(
    *,
    mode: str,
    run_number: int,
    candidates: list[ListingSchema],
    intent: PropertyIntent,
    analyze: Callable[
        [
            list[ListingSchema],
            PropertyIntent,
        ],
        tuple[
            list[RecommendationScore],
            list[dict[str, str]],
        ],
    ],
) -> tuple[
    BenchmarkRun,
    list[RecommendationScore],
]:
    """
    Time one candidate-analysis execution.
    """
    started_at = perf_counter()

    recommendations, errors = analyze(
        candidates,
        intent,
    )

    elapsed_seconds = (
        perf_counter() - started_at
    )

    benchmark_run = BenchmarkRun(
        mode=mode,
        run_number=run_number,
        elapsed_seconds=elapsed_seconds,
        candidate_count=len(candidates),
        successful_count=len(recommendations),
        error_count=len(errors),
    )

    if errors:
        print(
            f"\n{mode} run {run_number} "
            f"candidate errors:"
        )

        for error in errors:
            print(
                f"- {error['listing_key']}: "
                f"{error['error']}"
            )

    return benchmark_run, recommendations


def calculate_summary(
    runs: list[BenchmarkRun],
) -> dict[str, float]:
    elapsed_values = [
        run.elapsed_seconds
        for run in runs
    ]

    return {
        "minimum": min(elapsed_values),
        "maximum": max(elapsed_values),
        "mean": statistics.mean(
            elapsed_values
        ),
        "median": statistics.median(
            elapsed_values
        ),
    }


def save_results(
    runs: list[BenchmarkRun],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "mode",
                "run_number",
                "elapsed_seconds",
                "candidate_count",
                "successful_count",
                "error_count",
            ],
        )

        writer.writeheader()

        for run in runs:
            writer.writerow(
                {
                    "mode": run.mode,
                    "run_number": (
                        run.run_number
                    ),
                    "elapsed_seconds": round(
                        run.elapsed_seconds,
                        4,
                    ),
                    "candidate_count": (
                        run.candidate_count
                    ),
                    "successful_count": (
                        run.successful_count
                    ),
                    "error_count": (
                        run.error_count
                    ),
                }
            )


def main() -> None:
    search_agent = SearchAgent(
        repository=MySQLSearchRepository(),
    )

    workflow = PropertySearchGraph(
        search_agent=search_agent,
        parallel_candidate_analysis=True,
        max_parallel_candidates=(
            MAX_PARALLEL_CANDIDATES
        ),
    )

    print("=" * 80)
    print("SEQUENTIAL VS PARALLEL LATENCY BENCHMARK")
    print("=" * 80)
    print(f"Query: {QUERY}")
    print(
        "Parallel workers:",
        MAX_PARALLEL_CANDIDATES,
    )

    # Parse and search only once so both modes analyze
    # the exact same candidate objects.
    intent = workflow.intent_agent.run(
        QUERY
    )

    candidates = workflow.search_agent.run(
        intent,
        limit=workflow.SEARCH_CANDIDATE_LIMIT,
    )

    if not candidates:
        raise RuntimeError(
            "The benchmark query returned no candidates."
        )

    print(
        "Candidate count:",
        len(candidates),
    )

    # Warm-up is excluded from measured results.
    print("\nRunning warm-up...")

    warmup_recommendations, warmup_errors = (
        workflow._analyze_candidates_in_parallel(
            listings=candidates,
            intent=intent,
        )
    )

    if warmup_errors:
        raise RuntimeError(
            "Warm-up produced candidate errors: "
            f"{warmup_errors}"
        )

    if not warmup_recommendations:
        raise RuntimeError(
            "Warm-up produced no recommendations."
        )

    print("Warm-up complete.")

    sequential_runs: list[
        BenchmarkRun
    ] = []

    parallel_runs: list[
        BenchmarkRun
    ] = []

    all_runs: list[
        BenchmarkRun
    ] = []

    # Alternate execution order to reduce systematic
    # cache and machine-load bias.
    execution_orders = [
        ("sequential", "parallel"),
        ("parallel", "sequential"),
        ("sequential", "parallel"),
    ]

    for run_number, execution_order in enumerate(
        execution_orders,
        start=1,
    ):
        print(
            f"\nBenchmark pair {run_number}/"
            f"{RUNS_PER_MODE}"
        )

        pair_scores: dict[
            str,
            list[RecommendationScore],
        ] = {}

        for mode in execution_order:
            analyze = (
                workflow
                ._analyze_candidates_sequentially
                if mode == "sequential"
                else workflow
                ._analyze_candidates_in_parallel
            )

            benchmark_run, scores = run_analysis(
                mode=mode,
                run_number=run_number,
                candidates=candidates,
                intent=intent,
                analyze=analyze,
            )

            pair_scores[mode] = scores
            all_runs.append(benchmark_run)

            if mode == "sequential":
                sequential_runs.append(
                    benchmark_run
                )
            else:
                parallel_runs.append(
                    benchmark_run
                )

            if benchmark_run.error_count:
                raise AssertionError(
                    f"{mode} run produced "
                    f"{benchmark_run.error_count} "
                    "candidate errors."
                )

            print(
                f"{mode.title():<10} "
                f"{benchmark_run.elapsed_seconds:>8.2f}s "
                f"| successful: "
                f"{benchmark_run.successful_count} "
                f"| errors: "
                f"{benchmark_run.error_count}"
            )

        sequential_signature = ranked_signatures(
            workflow=workflow,
            recommendations=pair_scores[
                "sequential"
            ],
        )

        parallel_signature = ranked_signatures(
            workflow=workflow,
            recommendations=pair_scores[
                "parallel"
            ],
        )

        if (
            parallel_signature
            != sequential_signature
        ):
            raise AssertionError(
                f"Sequential and parallel outputs "
                f"differ in pair {run_number}."
            )

        print(
            "Output consistency: PASS"
        )

    sequential_summary = calculate_summary(
        sequential_runs
    )

    parallel_summary = calculate_summary(
        parallel_runs
    )

    sequential_median = (
        sequential_summary["median"]
    )

    parallel_median = (
        parallel_summary["median"]
    )

    speedup = (
        sequential_median
        / parallel_median
    )

    latency_reduction_percent = (
        (
            sequential_median
            - parallel_median
        )
        / sequential_median
        * 100
    )

    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)

    print(
        "Sequential runtimes:",
        [
            round(
                run.elapsed_seconds,
                2,
            )
            for run in sequential_runs
        ],
    )

    print(
        "Parallel runtimes:",
        [
            round(
                run.elapsed_seconds,
                2,
            )
            for run in parallel_runs
        ],
    )

    print(
        f"Sequential median: "
        f"{sequential_median:.2f}s"
    )

    print(
        f"Parallel median:   "
        f"{parallel_median:.2f}s"
    )

    print(
        f"Speedup:           "
        f"{speedup:.2f}x"
    )

    print(
        f"Latency reduction: "
        f"{latency_reduction_percent:.1f}%"
    )

    print(
        "Output consistency: PASS"
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    output_path = (
        OUTPUT_DIRECTORY
        / f"candidate_parallel_{timestamp}.csv"
    )

    save_results(
        runs=all_runs,
        output_path=output_path,
    )

    print(
        f"Raw results saved to: "
        f"{output_path}"
    )


if __name__ == "__main__":
    main()