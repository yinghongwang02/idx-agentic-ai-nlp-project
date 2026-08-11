from __future__ import annotations

import argparse
from pathlib import Path

from src.providers.factory import get_embedding_provider
from src.search.semantic_search import SemanticSearch


DEFAULT_INDEX_PATH = Path(
    "artifacts/embeddings/listing_embeddings.faiss"
)

DEFAULT_METADATA_PATH = Path(
    "artifacts/embeddings/listing_metadata.jsonl"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run semantic search over embedded MLS listings."
        )
    )

    parser.add_argument(
        "query",
        type=str,
        help="Natural-language semantic search query.",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of semantic results to return.",
    )

    parser.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX_PATH,
    )

    parser.add_argument(
        "--metadata",
        type=Path,
        default=DEFAULT_METADATA_PATH,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    provider = get_embedding_provider()

    searcher = SemanticSearch(
        provider=provider,
        index_path=args.index,
        metadata_path=args.metadata,
    )

    results = searcher.search(
        query=args.query,
        top_k=args.top_k,
    )

    print()
    print("=" * 100)
    print(f"Query: {args.query}")
    print(f"Results: {len(results)}")
    print("=" * 100)

    for rank, result in enumerate(
        results,
        start=1,
    ):
        print()
        print(f"Rank {rank}")
        print(f"Similarity: {result['score']:.4f}")
        print(f"Listing ID: {result.get('listing_id')}")
        print(f"City: {result.get('city')}")
        print(f"Price: {result.get('list_price')}")
        print(f"Bedrooms: {result.get('bedrooms')}")
        print(
            f"Property Type: "
            f"{result.get('property_type')}"
        )
        print(
            f"Text: "
            f"{result.get('embedding_text', '')[:500]}"
        )
        print("-" * 100)


if __name__ == "__main__":
    main()