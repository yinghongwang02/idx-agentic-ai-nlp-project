from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any

from src.evaluation.retrieval_cases import (
    RETRIEVAL_CASES,
    RetrievalEvaluationCase,
)
from src.evaluation.retrieval_metrics import (
    hard_constraint_pass_rate,
    preference_term_hit_rate,
)
from src.providers.factory import (
    get_embedding_provider,
)
from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema
from src.search.hybrid_search import HybridSearch
from src.search.mysql_search_repository import (
    MySQLSearchRepository,
)
from src.search.semantic_search import SemanticSearch


TOP_K = 5
CANDIDATE_LIMIT = 50

FAISS_INDEX_PATH = Path(
    "artifacts/embeddings/full/listing_embeddings.faiss"
)

EMBEDDINGS_PATH = Path(
    "artifacts/embeddings/full/listing_embeddings.npy"
)

METADATA_PATH = Path(
    "artifacts/embeddings/full/listing_metadata.jsonl"
)

OUTPUT_PATH = Path(
    "artifacts/benchmarks/retrieval_comparison_full.csv"
)


def timed_call(func):
    start = time.perf_counter()
    result = func()
    elapsed_ms = (
        time.perf_counter() - start
    ) * 1000

    return result, elapsed_ms


def build_intent(
    case: RetrievalEvaluationCase,
    keywords: list[str] | None = None,
) -> PropertyIntent:
    return PropertyIntent(
        city=case.city,
        max_price=case.max_price,
        min_bedrooms=case.min_bedrooms,
        min_bathrooms=case.min_bathrooms,
        property_type=case.property_type,
        keywords=keywords or [],
        preferences=[],
    )


def semantic_result_to_listing(
    result: dict[str, Any],
) -> ListingSchema:
    return ListingSchema(
        listing_key=str(
            result["listing_id"]
        ),
        unparsed_address=(
            result.get("address") or ""
        ),
        city=result.get("city") or "",
        postal_code=(
            str(result["zip"])
            if result.get("zip") is not None
            else None
        ),
        list_price=float(
            result.get("list_price") or 0
        ),
        bedrooms_total=(
            int(result["bedrooms"])
            if result.get("bedrooms")
            is not None
            else None
        ),
        bathrooms_total_integer=(
            int(result["bathrooms"])
            if result.get("bathrooms")
            is not None
            else None
        ),
        living_area=(
            float(result["living_area"])
            if result.get("living_area")
            is not None
            else None
        ),
        property_sub_type=(
            result.get("property_type")
        ),
        public_remarks=(
            result.get("embedding_text")
        ),
    )


def evaluate_mode(
    *,
    case: RetrievalEvaluationCase,
    mode: str,
    listings: list[ListingSchema],
    latency_ms: float,
    semantic_scores: list[float] | None = None,
) -> dict[str, Any]:
    avg_semantic_score = None

    if semantic_scores:
        avg_semantic_score = (
            sum(semantic_scores)
            / len(semantic_scores)
        )

    return {
        "case": case.name,
        "mode": mode,
        "result_count": len(listings),
        "latency_ms": round(
            latency_ms,
            2,
        ),
        "hard_constraint_pass_rate": round(
            hard_constraint_pass_rate(
                listings,
                case,
            ),
            4,
        ),
        "preference_term_hit_rate": round(
            preference_term_hit_rate(
                listings,
                case.preference_terms,
            ),
            4,
        ),
        "avg_semantic_score": (
            round(avg_semantic_score, 4)
            if avg_semantic_score
            is not None
            else None
        ),
    }


def run_case(
    case: RetrievalEvaluationCase,
    repository: MySQLSearchRepository,
    semantic_search: SemanticSearch,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    print()
    print("=" * 100)
    print(f"CASE: {case.name}")
    print("=" * 100)

    # ------------------------------------------------------------------
    # Structured
    # ------------------------------------------------------------------

    structured_intent = build_intent(
        case
    )

    structured, latency = timed_call(
        lambda: repository.search(
            structured_intent,
            limit=TOP_K,
        )
    )

    rows.append(
        evaluate_mode(
            case=case,
            mode="structured",
            listings=structured,
            latency_ms=latency,
        )
    )

    # ------------------------------------------------------------------
    # Keyword
    #
    # MVP comparison:
    # use the first preference term as an exact hard keyword.
    # ------------------------------------------------------------------

    keyword = (
        case.preference_terms[0]
        if case.preference_terms
        else None
    )

    keyword_results: list[
        ListingSchema
    ] = []

    keyword_latency = 0.0

    if keyword:
        keyword_intent = build_intent(
            case,
            keywords=[keyword],
        )

        (
            keyword_results,
            keyword_latency,
        ) = timed_call(
            lambda: repository.search(
                keyword_intent,
                limit=TOP_K,
            )
        )

    rows.append(
        evaluate_mode(
            case=case,
            mode="keyword",
            listings=keyword_results,
            latency_ms=keyword_latency,
        )
    )

    # ------------------------------------------------------------------
    # Pure semantic
    #
    # Uses current global 1000-listing FAISS artifact.
    # ------------------------------------------------------------------

    semantic_raw, semantic_latency = (
        timed_call(
            lambda: semantic_search.search(
                case.semantic_query,
                top_k=TOP_K,
            )
        )
    )

    semantic_listings = [
        semantic_result_to_listing(
            result
        )
        for result in semantic_raw
    ]

    semantic_scores = [
        result["score"]
        for result in semantic_raw
    ]

    rows.append(
        evaluate_mode(
            case=case,
            mode="semantic",
            listings=semantic_listings,
            latency_ms=semantic_latency,
            semantic_scores=semantic_scores,
        )
    )

    # ------------------------------------------------------------------
    # Hybrid
    #
    # For the formal comparison, use current shared embedding artifacts.
    # If overlap is low, record the reduced result count rather than hide it.
    # ------------------------------------------------------------------

    hybrid_candidates, sql_latency = (
        timed_call(
            lambda: repository.search(
                structured_intent,
                limit=CANDIDATE_LIMIT,
            )
        )
    )

    provider = get_embedding_provider()

    hybrid_search = HybridSearch(
        provider=provider,
        embeddings_path=EMBEDDINGS_PATH,
        metadata_path=METADATA_PATH,
    )

    hybrid_raw, rerank_latency = (
        timed_call(
            lambda: hybrid_search.rerank(
                candidates=hybrid_candidates,
                semantic_query=(
                    case.semantic_query
                ),
                top_k=TOP_K,
            )
        )
    )

    hybrid_listings = [
        result["listing"]
        for result in hybrid_raw
    ]

    hybrid_scores = [
        result["semantic_score"]
        for result in hybrid_raw
    ]

    rows.append(
        evaluate_mode(
            case=case,
            mode="hybrid",
            listings=hybrid_listings,
            latency_ms=(
                sql_latency
                + rerank_latency
            ),
            semantic_scores=hybrid_scores,
        )
    )

    for row in rows:
        print(row)

    return rows


def write_results(
    rows: list[dict[str, Any]],
) -> None:
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "case",
        "mode",
        "result_count",
        "latency_ms",
        "hard_constraint_pass_rate",
        "preference_term_hit_rate",
        "avg_semantic_score",
    ]

    with OUTPUT_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    print()
    print(
        f"Saved retrieval comparison: "
        f"{OUTPUT_PATH}"
    )


def main() -> None:
    repository = MySQLSearchRepository()

    provider = get_embedding_provider()

    semantic_search = SemanticSearch(
        provider=provider,
        index_path=FAISS_INDEX_PATH,
        metadata_path=METADATA_PATH,
    )

    all_rows: list[
        dict[str, Any]
    ] = []

    for case in RETRIEVAL_CASES:
        all_rows.extend(
            run_case(
                case=case,
                repository=repository,
                semantic_search=semantic_search,
            )
        )

    write_results(all_rows)


if __name__ == "__main__":
    main()