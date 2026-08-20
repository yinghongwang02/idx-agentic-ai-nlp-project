from __future__ import annotations

import json
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

TOP_K = 4


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


def print_case_results(
    case: dict[str, Any],
    results: list[dict[str, Any]],
    metrics: dict[str, Any] | None,
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
            f"  Top-{TOP_K} source hit: "
            f"{metrics['source_hit']}"
        )
        print(
            f"  Top-{TOP_K} section hit: "
            f"{metrics['section_hit']}"
        )
        print(
            f"  Top-{TOP_K} content hit: "
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

    unsupported_results: list[
        dict[str, Any]
    ] = []

    for case in cases:
        results = retriever.search(
            query=case["question"],
            top_k=TOP_K,
        )

        if case["answerable"]:
            answerable_count += 1

            metrics = evaluate_answerable_case(
                case,
                results,
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
            )

    print()
    print("=" * 100)
    print(
        "KNOWLEDGE RETRIEVAL EVALUATION SUMMARY"
    )
    print("=" * 100)

    print(
        f"Total cases:              "
        f"{len(cases)}"
    )
    print(
        f"Answerable cases:         "
        f"{answerable_count}"
    )
    print(
        f"Unsupported cases:        "
        f"{unsupported_count}"
    )

    if answerable_count:
        print(
            f"Top-1 source accuracy:    "
            f"{top1_source_hits}/{answerable_count} "
            f"= "
            f"{top1_source_hits / answerable_count:.1%}"
        )

        print(
            f"Top-{TOP_K} source hit rate:   "
            f"{source_hits}/{answerable_count} "
            f"= "
            f"{source_hits / answerable_count:.1%}"
        )

        print(
            f"Top-{TOP_K} section hit rate:  "
            f"{section_hits}/{answerable_count} "
            f"= "
            f"{section_hits / answerable_count:.1%}"
        )

        print(
            f"Top-{TOP_K} content hit rate:  "
            f"{content_hits}/{answerable_count} "
            f"= "
            f"{content_hits / answerable_count:.1%}"
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