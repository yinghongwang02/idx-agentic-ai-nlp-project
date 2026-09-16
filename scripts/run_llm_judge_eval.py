from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

from src.evaluation.llm_judge import LLMJudge
from src.orchestration.composition import create_orchestrator
from src.providers.factory import get_llm_provider


DEFAULT_CASES_PATH = Path(
    "eval/llm_judge_cases.json"
)

NEGATIVE_SCORE_THRESHOLD = 3


def load_cases(
    path: Path,
) -> list[dict[str, Any]]:
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        cases = json.load(file)

    if not isinstance(cases, list):
        raise ValueError(
            "LLM judge cases must be a JSON list."
        )

    return cases


def build_evidence(
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Preserve structured application outputs as judge evidence.

    final_response is intentionally excluded because it is the
    response being evaluated, not independent evidence.
    """

    return {
        "route": state.get("route"),
        "routes": state.get("routes"),
        "route_reason": state.get("route_reason"),
        "agents_invoked": state.get(
            "agents_invoked"
        ),
        "search_result": state.get(
            "search_result"
        ),
        "market_result": state.get(
            "market_result"
        ),
        "recommendation_result": state.get(
            "recommendation_result"
        ),
        "knowledge_result": state.get(
            "knowledge_result"
        ),
        "errors": state.get("errors"),
    }


def run_e2e_case(
    *,
    case: dict[str, Any],
    orchestrator: Any,
    judge: LLMJudge,
) -> dict[str, Any]:
    case_id = case["id"]
    query = case["query"]
    expected_route = case["expected_route"]

    state = orchestrator.invoke(
        query,
        session_id=f"llm-judge-{case_id}",
    )

    actual_route = state.get("route")
    final_response = state.get(
        "final_response",
        "",
    )

    route_match = (
        expected_route == actual_route
    )

    evidence = build_evidence(state)

    judge_result = judge.evaluate(
        user_query=query,
        response=final_response,
        evidence=evidence,
    )

    return {
        "id": case_id,
        "type": "e2e",
        "query": query,
        "expected_route": expected_route,
        "actual_route": actual_route,
        "route_match": route_match,
        "correctness": judge_result.correctness,
        "relevance": judge_result.relevance,
        "groundedness": judge_result.groundedness,
        "rationale": judge_result.rationale,
    }


def run_controlled_negative_case(
    *,
    case: dict[str, Any],
    judge: LLMJudge,
) -> dict[str, Any]:
    case_id = case["id"]
    query = case["query"]
    response = case["response"]
    evidence = case["evidence"]

    expected_low_dimension = case[
        "expected_low_dimension"
    ]

    judge_result = judge.evaluate(
        user_query=query,
        response=response,
        evidence=evidence,
    )

    scores = {
        "correctness": judge_result.correctness,
        "relevance": judge_result.relevance,
        "groundedness": judge_result.groundedness,
    }

    if expected_low_dimension not in scores:
        raise ValueError(
            "Unsupported expected_low_dimension: "
            f"{expected_low_dimension}"
        )

    target_score = scores[
        expected_low_dimension
    ]

    sensitivity_pass = (
        target_score <= NEGATIVE_SCORE_THRESHOLD
    )

    return {
        "id": case_id,
        "type": "controlled_negative",
        "query": query,
        "expected_low_dimension": (
            expected_low_dimension
        ),
        "sensitivity_pass": sensitivity_pass,
        "correctness": judge_result.correctness,
        "relevance": judge_result.relevance,
        "groundedness": judge_result.groundedness,
        "rationale": judge_result.rationale,
    }


def run_evaluation(
    cases_path: Path,
) -> list[dict[str, Any]]:
    cases = load_cases(cases_path)

    orchestrator = create_orchestrator()

    judge = LLMJudge(
        llm_provider=get_llm_provider()
    )

    results: list[dict[str, Any]] = []

    for index, case in enumerate(
        cases,
        start=1,
    ):
        case_id = case["id"]
        case_type = case.get(
            "type",
            "e2e",
        )

        print("=" * 80)
        print(
            f"[{index}/{len(cases)}] "
            f"{case_id} [{case_type}]"
        )

        if case_type == "e2e":
            print(
                f"Query: {case['query']}"
            )

            result = run_e2e_case(
                case=case,
                orchestrator=orchestrator,
                judge=judge,
            )

            print(
                f"Route: {result['actual_route']} "
                f"(expected="
                f"{result['expected_route']}, "
                f"match="
                f"{result['route_match']})"
            )

        elif case_type == "controlled_negative":
            print(
                f"Query: {case['query']}"
            )
            print(
                "Injected response: "
                f"{case['response']}"
            )

            result = (
                run_controlled_negative_case(
                    case=case,
                    judge=judge,
                )
            )

            print(
                "Expected low dimension: "
                f"{result['expected_low_dimension']}"
            )

            print(
                "Sensitivity detected: "
                f"{result['sensitivity_pass']}"
            )

        else:
            raise ValueError(
                f"Unsupported case type: {case_type}"
            )

        results.append(result)

        print(
            "Scores: "
            f"correctness="
            f"{result['correctness']}/5, "
            f"relevance="
            f"{result['relevance']}/5, "
            f"groundedness="
            f"{result['groundedness']}/5"
        )

        print(
            f"Rationale: {result['rationale']}"
        )

    return results


def print_e2e_summary(
    results: list[dict[str, Any]],
) -> None:
    if not results:
        return

    route_accuracy = mean(
        1.0 if result["route_match"] else 0.0
        for result in results
    )

    correctness = mean(
        result["correctness"]
        for result in results
    )

    relevance = mean(
        result["relevance"]
        for result in results
    )

    groundedness = mean(
        result["groundedness"]
        for result in results
    )

    print()
    print("-" * 80)
    print("POSITIVE E2E CASES")
    print("-" * 80)
    print(
        f"Cases:              {len(results)}"
    )
    print(
        f"Route accuracy:     {route_accuracy:.1%}"
    )
    print(
        f"Correctness:        {correctness:.2f}/5"
    )
    print(
        f"Relevance:          {relevance:.2f}/5"
    )
    print(
        f"Groundedness:       {groundedness:.2f}/5"
    )


def print_negative_summary(
    results: list[dict[str, Any]],
) -> None:
    if not results:
        return

    sensitivity_rate = mean(
        1.0
        if result["sensitivity_pass"]
        else 0.0
        for result in results
    )

    correctness = mean(
        result["correctness"]
        for result in results
    )

    relevance = mean(
        result["relevance"]
        for result in results
    )

    groundedness = mean(
        result["groundedness"]
        for result in results
    )

    print()
    print("-" * 80)
    print("CONTROLLED NEGATIVE CASES")
    print("-" * 80)
    print(
        f"Cases:              {len(results)}"
    )
    print(
        "Sensitivity rate:   "
        f"{sensitivity_rate:.1%}"
    )
    print(
        f"Correctness:        {correctness:.2f}/5"
    )
    print(
        f"Relevance:          {relevance:.2f}/5"
    )
    print(
        f"Groundedness:       {groundedness:.2f}/5"
    )

    print()
    print("Sensitivity checks:")

    for result in results:
        status = (
            "PASS"
            if result["sensitivity_pass"]
            else "FAIL"
        )

        dimension = result[
            "expected_low_dimension"
        ]

        score = result[dimension]

        print(
            f"- {result['id']}: "
            f"{dimension}={score}/5 "
            f"-> {status}"
        )


def print_summary(
    results: list[dict[str, Any]],
) -> None:
    if not results:
        print("No evaluation results.")
        return

    e2e_results = [
        result
        for result in results
        if result["type"] == "e2e"
    ]

    negative_results = [
        result
        for result in results
        if result["type"]
        == "controlled_negative"
    ]

    print()
    print("=" * 80)
    print("LLM-AS-JUDGE SUMMARY")
    print("=" * 80)

    print_e2e_summary(
        e2e_results
    )

    print_negative_summary(
        negative_results
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run offline LLM-as-Judge evaluation "
            "against the Unified Copilot."
        )
    )

    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES_PATH,
    )

    args = parser.parse_args()

    results = run_evaluation(
        args.cases
    )

    print_summary(results)


if __name__ == "__main__":
    main()