from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.orchestration.composition import (
    create_orchestrator,
)


LISTING_METADATA_PATH = Path(
    "artifacts/embeddings/full/"
    "listing_metadata.jsonl"
)


def get_real_listing_id() -> str:
    """
    Read one real listing ID directly from the existing
    full-corpus embedding metadata.

    This guarantees that the recommendation smoke test
    uses a target present in SimilarListingRetriever.
    """

    with LISTING_METADATA_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            if not line.strip():
                continue

            record = json.loads(line)

            listing_id = record.get(
                "listing_id"
            )

            if listing_id is not None:
                return str(listing_id)

    raise RuntimeError(
        "No listing_id found in listing metadata."
    )


def print_result(
    name: str,
    result: dict[str, Any],
) -> None:
    print()
    print("=" * 100)
    print(name)
    print("=" * 100)

    print(
        "Route:",
        result.get("route"),
    )

    print(
        "Routes:",
        result.get("routes"),
    )

    print(
        "Agents invoked:",
        result.get("agents_invoked"),
    )

    print(
        "Errors:",
        result.get("errors", []),
    )

    print("\nFinal response:")
    print(
        result.get(
            "final_response",
            "",
        )
    )


def main() -> None:
    print(
        "Creating real Week 9 orchestrator..."
    )

    orchestrator = create_orchestrator()

    print(
        "Orchestrator created successfully."
    )

    # -----------------------------------------------------------------
    # 1. Knowledge
    # -----------------------------------------------------------------

    knowledge_result = orchestrator.invoke(
        "What does DOM mean in real estate?"
    )

    print_result(
        "SMOKE 1 - KNOWLEDGE",
        knowledge_result,
    )

    # -----------------------------------------------------------------
    # 2. Market
    # -----------------------------------------------------------------

    market_result = orchestrator.invoke(
        "Are Irvine home prices rising?"
    )

    print_result(
        "SMOKE 2 - MARKET",
        market_result,
    )

    # -----------------------------------------------------------------
    # 3. Search
    # -----------------------------------------------------------------

    search_result = orchestrator.invoke(
        (
            "Find homes in Irvine under "
            "$1.5 million."
        )
    )

    print_result(
        "SMOKE 3 - SEARCH",
        search_result,
    )

    # -----------------------------------------------------------------
    # 4. Mixed Search + Market
    # -----------------------------------------------------------------

    mixed_result = orchestrator.invoke(
        (
            "Find homes in Irvine under "
            "$1.5 million and tell me "
            "whether home prices are rising."
        )
    )

    print_result(
        "SMOKE 4 - MIXED",
        mixed_result,
    )

    # -----------------------------------------------------------------
    # 5. Similar-home recommendation
    # -----------------------------------------------------------------

    target_listing_id = (
        get_real_listing_id()
    )

    print()
    print(
        "Recommendation target listing:",
        target_listing_id,
    )

    recommendation_result = (
        orchestrator.invoke(
            (
                "Show me homes similar to "
                f"listing {target_listing_id}."
            )
        )
    )

    print_result(
        "SMOKE 5 - RECOMMENDATION",
        recommendation_result,
    )


if __name__ == "__main__":
    main()