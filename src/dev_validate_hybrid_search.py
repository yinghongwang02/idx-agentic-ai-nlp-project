from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from src.providers.factory import get_embedding_provider
from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema
from src.search.hybrid_search import HybridSearch
from src.search.mysql_search_repository import MySQLSearchRepository


DEFAULT_CANDIDATE_LIMIT = 50
DEFAULT_TOP_K = 5

TEMP_DIR = Path(
    "artifacts/embeddings/hybrid_validation"
)

TEMP_EMBEDDINGS_PATH = (
    TEMP_DIR / "listing_embeddings.npy"
)

TEMP_METADATA_PATH = (
    TEMP_DIR / "listing_metadata.jsonl"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate hybrid search by embedding "
            "the exact structured candidate set."
        )
    )

    parser.add_argument(
        "--city",
        type=str,
        required=True,
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
    )

    parser.add_argument(
        "--preference",
        action="append",
        default=[],
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

    args = parser.parse_args()

    if not args.preference:
        parser.error(
            "At least one --preference is required."
        )

    if args.candidate_limit <= 0:
        parser.error(
            "--candidate-limit must be greater than zero."
        )

    if args.top_k <= 0:
        parser.error(
            "--top-k must be greater than zero."
        )

    return args


def build_semantic_query(
    preferences: list[str],
) -> str:
    cleaned = [
        value.strip()
        for value in preferences
        if value.strip()
    ]

    if not cleaned:
        raise ValueError(
            "Semantic preferences must not be empty."
        )

    return ", ".join(cleaned)


def build_candidate_embedding_text(
    listing: ListingSchema,
) -> str:
    """
    Build semantic text from a structured-search candidate.

    This mirrors the intent of the main listing embedding
    representation while using fields available on ListingSchema.
    """
    parts: list[str] = []

    if listing.property_sub_type:
        parts.append(
            f"Property type: "
            f"{listing.property_sub_type}."
        )

    if listing.city:
        parts.append(
            f"Location: {listing.city}."
        )

    features: list[str] = []

    if listing.bedrooms_total is not None:
        features.append(
            f"{listing.bedrooms_total} bedrooms"
        )

    if listing.bathrooms_total_integer is not None:
        features.append(
            f"{listing.bathrooms_total_integer} bathrooms"
        )

    if listing.living_area is not None:
        features.append(
            f"{listing.living_area:g} square feet"
        )

    if features:
        parts.append(
            f"Features: {', '.join(features)}."
        )

    if listing.list_price is not None:
        parts.append(
            f"List price: "
            f"${listing.list_price:,.0f}."
        )

    if listing.public_remarks:
        remarks = " ".join(
            listing.public_remarks.split()
        )

        parts.append(
            f"Description: {remarks}"
        )

    text = " ".join(parts).strip()

    if not text:
        raise ValueError(
            f"Listing {listing.listing_key} "
            "has no usable embedding text."
        )

    return text


def build_candidate_artifacts(
    candidates: list[ListingSchema],
) -> int:
    """
    Generate temporary embeddings and metadata for the exact
    structured candidate set.

    Returns the number of candidates successfully embedded.
    """
    provider = get_embedding_provider()

    valid_candidates: list[ListingSchema] = []
    texts: list[str] = []

    for candidate in candidates:
        try:
            text = build_candidate_embedding_text(
                candidate
            )
        except ValueError:
            continue

        valid_candidates.append(candidate)
        texts.append(text)

    if not texts:
        raise RuntimeError(
            "No candidate embedding texts could be built."
        )

    print(
        f"\nGenerating embeddings for "
        f"{len(texts)} structured candidates..."
    )

    raw_embeddings = provider.embed_documents(
        texts
    )

    embeddings = np.asarray(
        raw_embeddings,
        dtype=np.float32,
    )

    if embeddings.ndim != 2:
        raise RuntimeError(
            "Expected a 2D embedding matrix."
        )

    if embeddings.shape[0] != len(valid_candidates):
        raise RuntimeError(
            "Embedding count does not match "
            "candidate count."
        )

    if not np.isfinite(embeddings).all():
        raise RuntimeError(
            "Candidate embeddings contain "
            "NaN or infinite values."
        )

    TEMP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    np.save(
        TEMP_EMBEDDINGS_PATH,
        embeddings,
    )

    with TEMP_METADATA_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        for row_index, (
            candidate,
            text,
        ) in enumerate(
            zip(valid_candidates, texts)
        ):
            record: dict[str, Any] = {
                "embedding_row": row_index,
                "listing_id": str(
                    candidate.listing_key
                ),
                "city": candidate.city,
                "list_price": (
                    candidate.list_price
                ),
                "bedrooms": (
                    candidate.bedrooms_total
                ),
                "property_type": (
                    candidate.property_sub_type
                ),
                "embedding_text": text,
            }

            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    return len(valid_candidates)


def print_original_candidates(
    candidates: list[ListingSchema],
    limit: int = 5,
) -> None:
    print("\n" + "=" * 100)
    print("ORIGINAL STRUCTURED SEARCH ORDER")
    print(
        "(MySQL currently orders candidates "
        "by list price ascending)"
    )
    print("=" * 100)

    for rank, listing in enumerate(
        candidates[:limit],
        start=1,
    ):
        print(
            f"{rank}. "
            f"{listing.listing_key} | "
            f"{listing.city} | "
            f"${listing.list_price:,.0f}"
        )


def print_hybrid_results(
    results: list[dict[str, Any]],
) -> None:
    print("\n" + "=" * 100)
    print("HYBRID SEMANTIC RANKING")
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
            f"City: {listing.city}"
        )
        print(
            f"Price: ${listing.list_price:,.0f}"
        )
        print(
            f"Bedrooms: "
            f"{listing.bedrooms_total}"
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
    print("HYBRID SEARCH VALIDATION")
    print("=" * 100)

    print(
        f"Structured candidates: "
        f"{len(candidates)}"
    )
    print(
        f"Semantic query: "
        f"{semantic_query}"
    )

    if not candidates:
        print(
            "No structured candidates found."
        )
        return

    print_original_candidates(
        candidates,
        limit=args.top_k,
    )

    embedded_count = (
        build_candidate_artifacts(
            candidates
        )
    )

    print(
        f"\nEmbedded candidate coverage: "
        f"{embedded_count}/{len(candidates)}"
    )

    provider = get_embedding_provider()

    hybrid_search = HybridSearch(
        provider=provider,
        embeddings_path=TEMP_EMBEDDINGS_PATH,
        metadata_path=TEMP_METADATA_PATH,
    )

    results = hybrid_search.rerank(
        candidates=candidates,
        semantic_query=semantic_query,
        top_k=args.top_k,
    )

    print_hybrid_results(results)


if __name__ == "__main__":
    main()