from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import tiktoken


DEFAULT_METADATA_PATH = Path(
    "artifacts/embeddings/sample_1000/listing_metadata.jsonl"
)

DEFAULT_FULL_COUNT = 53_000

# Current text-embedding-3-small price.
DEFAULT_PRICE_PER_MILLION_TOKENS = 0.02


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit token usage of existing listing embedding text "
            "and estimate full-corpus embedding cost."
        )
    )

    parser.add_argument(
        "--metadata",
        type=Path,
        default=DEFAULT_METADATA_PATH,
    )

    parser.add_argument(
        "--full-count",
        type=int,
        default=DEFAULT_FULL_COUNT,
        help="Estimated number of full-corpus eligible listings.",
    )

    parser.add_argument(
        "--price-per-million",
        type=float,
        default=DEFAULT_PRICE_PER_MILLION_TOKENS,
    )

    return parser.parse_args()


def load_embedding_texts(
    metadata_path: Path,
) -> list[str]:
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {metadata_path}"
        )

    texts: list[str] = []

    with metadata_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            if not line.strip():
                continue

            record = json.loads(line)

            text = record.get("embedding_text")

            if not text or not text.strip():
                continue

            texts.append(text)

    if not texts:
        raise RuntimeError(
            "No embedding_text values were found."
        )

    return texts


def count_tokens(
    texts: list[str],
) -> np.ndarray:
    # text-embedding-3-small uses the cl100k_base encoding family.
    encoding = tiktoken.get_encoding(
        "cl100k_base"
    )

    counts = [
        len(encoding.encode(text))
        for text in texts
    ]

    return np.asarray(
        counts,
        dtype=np.int32,
    )


def estimate_cost(
    tokens_per_listing: float,
    listing_count: int,
    price_per_million: float,
) -> tuple[float, float]:
    total_tokens = (
        tokens_per_listing
        * listing_count
    )

    estimated_cost = (
        total_tokens
        / 1_000_000
        * price_per_million
    )

    return total_tokens, estimated_cost


def main() -> None:
    args = parse_args()

    if args.full_count <= 0:
        raise ValueError(
            "--full-count must be greater than zero."
        )

    texts = load_embedding_texts(
        args.metadata
    )

    token_counts = count_tokens(
        texts
    )

    sample_count = len(token_counts)

    mean_tokens = float(
        np.mean(token_counts)
    )
    median_tokens = float(
        np.median(token_counts)
    )
    p95_tokens = float(
        np.percentile(
            token_counts,
            95,
        )
    )
    min_tokens = int(
        np.min(token_counts)
    )
    max_tokens = int(
        np.max(token_counts)
    )
    total_sample_tokens = int(
        np.sum(token_counts)
    )

    (
        estimated_tokens_mean,
        estimated_cost_mean,
    ) = estimate_cost(
        mean_tokens,
        args.full_count,
        args.price_per_million,
    )

    (
        estimated_tokens_p95,
        estimated_cost_p95,
    ) = estimate_cost(
        p95_tokens,
        args.full_count,
        args.price_per_million,
    )

    print("=" * 80)
    print("LISTING EMBEDDING TOKEN AUDIT")
    print("=" * 80)

    print(
        f"Sample listings:       "
        f"{sample_count:,}"
    )
    print(
        f"Sample total tokens:   "
        f"{total_sample_tokens:,}"
    )
    print(
        f"Mean tokens/listing:   "
        f"{mean_tokens:,.2f}"
    )
    print(
        f"Median tokens/listing: "
        f"{median_tokens:,.2f}"
    )
    print(
        f"P95 tokens/listing:    "
        f"{p95_tokens:,.2f}"
    )
    print(
        f"Min tokens/listing:    "
        f"{min_tokens:,}"
    )
    print(
        f"Max tokens/listing:    "
        f"{max_tokens:,}"
    )

    print()
    print("=" * 80)
    print("FULL-CORPUS COST ESTIMATE")
    print("=" * 80)

    print(
        f"Full listing count:    "
        f"{args.full_count:,}"
    )
    print(
        f"Price / 1M tokens:     "
        f"${args.price_per_million:.4f}"
    )

    print()
    print("Mean-based estimate:")
    print(
        f"  Tokens: "
        f"{estimated_tokens_mean:,.0f}"
    )
    print(
        f"  Cost:   "
        f"${estimated_cost_mean:.4f}"
    )

    print()
    print(
        "Conservative P95-every-listing estimate:"
    )
    print(
        f"  Tokens: "
        f"{estimated_tokens_p95:,.0f}"
    )
    print(
        f"  Cost:   "
        f"${estimated_cost_p95:.4f}"
    )

    print()
    print(
        "Note: the P95 estimate assumes every full-corpus "
        "listing is as long as the sample P95 listing, "
        "so it is intentionally conservative."
    )


if __name__ == "__main__":
    main()