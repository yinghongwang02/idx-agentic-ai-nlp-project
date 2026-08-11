from __future__ import annotations

import argparse
from pathlib import Path

from src.providers.factory import get_embedding_provider
from src.schemas.intent_schema import PropertyIntent
from src.search.hybrid_search import HybridSearch
from src.search.mysql_search_repository import MySQLSearchRepository


DEFAULT_EMBEDDINGS_PATH = Path(
    "artifacts/embeddings/listing_embeddings.npy"
)

DEFAULT_METADATA_PATH = Path(
    "artifacts/embeddings/listing_metadata.jsonl"
)

DEFAULT_CANDIDATE_LIMIT = 50
DEFAULT_TOP_K = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run structured MLS filtering followed by "
            "semantic candidate reranking."
        )
    )

    parser.add_argument(
        "--city",
        type=str,
        default=None,
    )

    parser.add_argument(
        "--max-price",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--min-bedrooms",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--min-bathrooms",
        type=float,
        default=None,
    )

    parser.add_argument(
        "--property-type",
        type=str,
        default=None,
    )

    parser.add_argument(
        "--keyword",
        action="append",
        default=[],
        help=(
            "Hard keyword requirement. "
            "May be supplied multiple times."
        ),
    )

    parser.add_argument(
        "--preference",
        action="append",
        default=[],
        help=(
            "Soft semantic preference. "
            "May be supplied multiple times."
        ),
    )

    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=DEFAULT_CANDIDATE_LIMIT,
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
    )

    parser.add_argument(
        "--embeddings",
        type=Path,
        default=DEFAULT_EMBEDDINGS_PATH,
    )

    parser.add_argument(
        "--metadata",
        type=Path,
        default=DEFAULT_METADATA_PATH,
    )

    args = parser.parse_args()

    if args.candidate_limit <= 0:
        parser.error(
            "--candidate-limit must be greater than zero."
        )

    if args.top_k <= 0:
        parser.error(
            "--top-k must be greater than zero."
        )

    if not args.preference:
        parser.error(
            "At least one --preference is required "
            "for hybrid semantic reranking."
        )

    return args


def build_semantic_query(
    preferences: list[str],
) -> str:
    cleaned = [
        preference.strip()
        for preference in preferences
        if preference.strip()
    ]

    if not cleaned:
        raise ValueError(
            "At least one non-empty semantic preference "
            "is required."
        )

    return ", ".join(cleaned)


def print_structured_constraints(
    intent: PropertyIntent,
) -> None:
    print("\nStructured constraints:")

    constraints = [
        ("City", intent.city),
        ("Max price", intent.max_price),
        ("Min bedrooms", intent.min_bedrooms),
        ("Min bathrooms", intent.min_bathrooms),
        ("Property type", intent.property_type),
        ("Hard keywords", intent.keywords or None),
    ]

    for label, value in constraints:
        if value is not None:
            print(f"  {label}: {value}")


def main() -> None:
    args = parse_args()

    intent = PropertyIntent(
        city=args.city,
        max_price=args.max_price,
        min_bedrooms=args.min_bedrooms,
        min_bathrooms=args.min_bathrooms,
        property_type=args.property_type,
        keywords=args.keyword,
        preferences=args.preference,
    )

    semantic_query = build_semantic_query(
        intent.preferences
    )

    repository = MySQLSearchRepository()

    candidates = repository.search(
        intent=intent,
        limit=args.candidate_limit,
    )

    print("=" * 100)
    print("HYBRID MLS SEARCH")
    print("=" * 100)

    print_structured_constraints(intent)

    print(
        f"\nSemantic preferences: "
        f"{semantic_query}"
    )

    print(
        f"\nStructured candidates returned: "
        f"{len(candidates)}"
    )

    if not candidates:
        print(
            "\nNo listings satisfied the structured "
            "constraints."
        )
        return

    provider = get_embedding_provider()

    searcher = HybridSearch(
        provider=provider,
        embeddings_path=args.embeddings,
        metadata_path=args.metadata,
    )

    results = searcher.rerank(
        candidates=candidates,
        semantic_query=semantic_query,
        top_k=args.top_k,
    )

    print(
        f"Candidates with available embeddings: "
        f"{len(results)} returned in Top-K"
    )

    if not results:
        print(
            "\nStructured candidates were found, but none "
            "were present in the current embedding artifacts."
        )
        return

    print("\n" + "=" * 100)
    print("SEMANTICALLY RERANKED RESULTS")
    print("=" * 100)

    for rank, result in enumerate(
        results,
        start=1,
    ):
        listing = result["listing"]

        print()
        print(f"Rank {rank}")
        print(
            f"Semantic score: "
            f"{result['semantic_score']:.4f}"
        )
        print(
            f"Listing ID: {listing.listing_key}"
        )
        print(
            f"Address: {listing.unparsed_address}"
        )
        print(
            f"City: {listing.city}"
        )
        print(
            f"Price: ${listing.list_price:,.0f}"
        )
        print(
            f"Bedrooms: {listing.bedrooms_total}"
        )
        print(
            f"Bathrooms: "
            f"{listing.bathrooms_total_integer}"
        )
        print(
            f"Property type: "
            f"{listing.property_sub_type}"
        )

        remarks = listing.public_remarks or ""

        print(
            f"Remarks: {remarks[:500]}"
        )

        print("-" * 100)


if __name__ == "__main__":
    main()