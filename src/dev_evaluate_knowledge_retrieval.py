from __future__ import annotations

import json
import argparse
from pathlib import Path
from typing import Any

from src.providers.factory import get_embedding_provider
from src.search.knowledge_retriever import KnowledgeRetriever


DEFAULT_CASES_PATH = Path(
    "eval/knowledge_retrieval_cases.json"
)

DEFAULT_INDEX_PATH = Path(
    "artifacts/knowledge/knowledge.faiss"
)

DEFAULT_METADATA_PATH = Path(
    "artifacts/knowledge/knowledge_metadata.jsonl"
)

TOP_K = 6

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Evaluate knowledge retrieval quality."
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=TOP_K,
        help=(
            "Number of retrieved chunks per query. "
            f"Default: {TOP_K}."
        ),
    )

    return parser.parse_args()


def load_cases(
    path: Path,
) -> list[dict[str, Any]]:
    """Load knowledge retrieval evaluation cases."""

    if not path.exists():
        raise FileNotFoundError(
            f"Evaluation cases not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        cases = json.load(file)

    if not isinstance(cases, list):
        raise ValueError(
            "Evaluation cases must be a JSON list."
        )

    if not cases:
        raise ValueError(
            "Evaluation case list is empty."
        )

    return cases


def contains_expected_terms(
    result: dict[str, Any],
    expected_terms: list[str],
) -> bool:
    """Check whether one chunk contains all expected terms."""

    if not expected_terms:
        return False

    text = str(
        result.get("text", "")
    ).lower()

    return all(
        term.lower() in text
        for term in expected_terms
    )


def evaluate_answerable_case(case, results):
    expected_sources = case.get("expected_sources")

    if expected_sources is None:
        expected_source = case.get("expected_source")
        expected_sources = [expected_source] if expected_source else []

    expected_section = case.get("expected_section")
    expected_terms = case.get("expected_terms", [])

    top1_source_hit = (
        bool(results)
        and results[0].get("source") in expected_sources
    )

    retrieved_sources = {
        result.get("source")
        for result in results
    }

    topk_source_hit = any(
        source in retrieved_sources
        for source in expected_sources
    )

    all_expected_sources_hit = all(
        source in retrieved_sources
        for source in expected_sources
    )

    topk_section_hit = True
    if expected_section:
        topk_section_hit = any(
            result.get("section") == expected_section
            for result in results
        )

    combined_content = " ".join(
        result.get("text", "")
        for result in results
    ).lower()

    topk_content_hit = all(
        term.lower() in combined_content
        for term in expected_terms
    )

    return {
        "top1_source_hit": top1_source_hit,

        # Main evaluation metrics
        "source_hit": all_expected_sources_hit,
        "section_hit": topk_section_hit,
        "content_hit": topk_content_hit,

        # Extra diagnostics
        "topk_source_hit": topk_source_hit,
        "all_expected_sources_hit": all_expected_sources_hit,
    }

def get_failure_reasons(
    case: dict[str, Any],
    metrics: dict[str, Any],
) -> list[str]:
    """Return interpretable failure reasons for one answerable case."""

    reasons: list[str] = []

    expected_sources = case.get("expected_sources")

    if expected_sources is None:
        expected_source = case.get("expected_source")
        expected_sources = (
            [expected_source]
            if expected_source
            else []
        )

    # Source-level failure
    if not metrics["source_hit"]:
        if len(expected_sources) > 1:
            reasons.append("CROSS_SOURCE_MISS")
        else:
            reasons.append("SOURCE_MISS")

    # Section-level failure
    if (
        case.get("expected_section")
        and not metrics["section_hit"]
    ):
        reasons.append("SECTION_MISS")

    # Expected content missing
    if not metrics["content_hit"]:
        reasons.append("CONTENT_MISS")

    # Top-K succeeded, but expected source was not rank 1
    if (
        not metrics["top1_source_hit"]
        and metrics["source_hit"]
    ):
        reasons.append("TOP1_RANKING_MISS")

    return reasons


def print_case_results(
    case: dict[str, Any],
    results: list[dict[str, Any]],
    metrics: dict[str, Any] | None,
    top_k: int,
) -> None:
    """Print readable evaluation output for one case."""

    print()
    print("=" * 100)
    print(
        f"CASE: {case['id']}"
    )
    print(
        f"QUESTION: {case['question']}"
    )
    print("=" * 100)

    for rank, result in enumerate(
        results,
        start=1,
    ):
        print(
            f"\nRank {rank}"
        )
        print(
            f"Score:   "
            f"{result.get('score', 0.0):.4f}"
        )
        print(
            f"Source:  "
            f"{result.get('source')}"
        )
        print(
            f"Section: "
            f"{result.get('section')}"
        )
        print(
            f"Chunk:   "
            f"{result.get('chunk_id')}"
        )

    if metrics is not None:
        print("\nEvaluation:")
        print(
            f"  Top-1 source hit: "
            f"{metrics['top1_source_hit']}"
        )
        print(
            f"  Top-{top_k} source hit: "
            f"{metrics['source_hit']}"
        )
        print(
            f"  Top-{top_k} section hit: "
            f"{metrics['section_hit']}"
        )
        print(
            f"  Top-{top_k} content hit: "
            f"{metrics['content_hit']}"
        )
    else:
        max_score = (
            results[0].get("score")
            if results
            else None
        )

        print("\nUnsupported case:")
        print(
            f"  Max retrieval score: "
            f"{max_score:.4f}"
            if max_score is not None
            else "  Max retrieval score: N/A"
        )


def main() -> None:
    args = parse_args()
    top_k = args.top_k

    cases = load_cases(
        DEFAULT_CASES_PATH
    )

    provider = get_embedding_provider()

    retriever = KnowledgeRetriever(
        provider=provider,
        index_path=DEFAULT_INDEX_PATH,
        metadata_path=DEFAULT_METADATA_PATH,
    )

    answerable_count = 0
    unsupported_count = 0

    top1_source_hits = 0
    source_hits = 0
    section_hits = 0
    content_hits = 0

    failure_results: list[
        dict[str, Any]
    ] = []

    unsupported_results: list[
        dict[str, Any]
    ] = []

    for case in cases:
        results = retriever.search(
            query=case["question"],
            top_k=top_k,
        )

        if case["answerable"]:
            answerable_count += 1

            metrics = evaluate_answerable_case(
                case,
                results,
            )

            failure_reasons = get_failure_reasons(
                case,
                metrics,
            )

            if failure_reasons:
                failure_results.append(
                    {
                        "id": case["id"],
                        "reasons": failure_reasons,
                    }
                )

            top1_source_hits += int(
                metrics["top1_source_hit"]
            )

            source_hits += int(
                metrics["source_hit"]
            )

            section_hits += int(
                metrics["section_hit"]
            )

            content_hits += int(
                metrics["content_hit"]
            )

            print_case_results(
                case,
                results,
                metrics,
                top_k,
            )

        else:
            unsupported_count += 1

            max_score = (
                float(results[0]["score"])
                if results
                else None
            )

            unsupported_results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "max_score": max_score,
                }
            )

            print_case_results(
                case,
                results,
                metrics=None,
                top_k=top_k,
            )

    print()
    print("=" * 100)
    print(
        "KNOWLEDGE RETRIEVAL EVALUATION SUMMARY"
    )
    print("=" * 100)

    print(
        f"Top-K:                   "
        f"{top_k}"
    )

    print(
        f"Total cases:             "
        f"{len(cases)}"
    )

    print(
        f"Answerable cases:        "
        f"{answerable_count}"
    )

    print(
        f"Unsupported cases:       "
        f"{unsupported_count}"
    )

    if answerable_count:
        print(
            f"Top-1 source accuracy:   "
            f"{top1_source_hits}/{answerable_count} "
            f"= "
            f"{top1_source_hits / answerable_count:.1%}"
        )

        print(
            f"Top-{top_k} source hit rate:  "
            f"{source_hits}/{answerable_count} "
            f"= "
            f"{source_hits / answerable_count:.1%}"
        )

        print(
            f"Top-{top_k} section hit rate: "
            f"{section_hits}/{answerable_count} "
            f"= "
            f"{section_hits / answerable_count:.1%}"
        )

        print(
            f"Top-{top_k} content hit rate: "
            f"{content_hits}/{answerable_count} "
            f"= "
            f"{content_hits / answerable_count:.1%}"
        )

    if failure_results:
        print("\nFailure / diagnostic report:")

        for item in failure_results:
            reasons_text = ", ".join(
                item["reasons"]
            )

            print(
                f"  {item['id']}: "
                f"{reasons_text}"
            )

    if unsupported_results:
        print("\nUnsupported cases:")

        for item in unsupported_results:
            score_text = (
                f"{item['max_score']:.4f}"
                if item["max_score"] is not None
                else "N/A"
            )

            print(
                f"  {item['id']}: "
                f"max_score={score_text}"
            )

if __name__ == "__main__":
    main()