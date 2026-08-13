from __future__ import annotations

import argparse
from pathlib import Path

from src.agents.comparable_value_agent import (
    ComparableValueAgent,
)
from src.agents.market_agent import MarketAgent
from src.recommendation.hybrid_recommendation import (
    HybridRecommendationService,
)
from src.recommendation.hybrid_similarity import (
    SimilarListingRetriever,
)
from src.search.mysql_sold_comp_repository import (
    MySQLSoldCompRepository,
)


DEFAULT_EMBEDDINGS_PATH = Path(
    "artifacts/embeddings/full/"
    "listing_embeddings.npy"
)

DEFAULT_METADATA_PATH = Path(
    "artifacts/embeddings/full/"
    "listing_metadata.jsonl"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Find listings similar to a target MLS "
            "listing using structured and semantic "
            "similarity."
        )
    )

    parser.add_argument(
        "listing_id",
        type=str,
        help=(
            "MLS listing ID used as the "
            "recommendation target."
        ),
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
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

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    retriever = SimilarListingRetriever(
        embeddings_path=args.embeddings,
        metadata_path=args.metadata,
    )

    sold_comp_repository = (
        MySQLSoldCompRepository()
    )

    market_agent = MarketAgent(
        repository=sold_comp_repository,
    )

    comparable_value_agent = (
        ComparableValueAgent()
    )

    service = HybridRecommendationService(
        similarity_retriever=retriever,
        market_agent=market_agent,
        comparable_value_agent=(
            comparable_value_agent
        ),
    )

    results = service.recommend(
        target_listing_id=args.listing_id,
        top_k=args.top_k,
    )

    print("=" * 100)
    print(
        "HYBRID SIMILAR-LISTING RECOMMENDATION"
    )
    print("=" * 100)

    print(
        f"Target listing: "
        f"{args.listing_id}"
    )

    print(
        f"Recommendations: "
        f"{len(results)}"
    )

    for rank, result in enumerate(
        results,
        start=1,
    ):
        listing = result["listing"]

        print()
        print(f"Rank {rank}")

        print(
            f"Hybrid similarity: "
            f"{result['hybrid_similarity_score']:.2f}"
        )

        print(
            f"Structured similarity: "
            f"{result['structured_similarity_score']:.2f}/60"
        )

        print(
            f"Semantic similarity: "
            f"{result['semantic_similarity']:.4f}"
        )

        print(
            f"Semantic contribution: "
            f"{result['semantic_similarity_score']:.2f}/40"
        )

        print(
            f"Listing ID: "
            f"{listing.listing_key}"
        )

        print(
            f"Address: "
            f"{listing.unparsed_address}"
        )

        print(
            f"City: "
            f"{listing.city}"
        )

        print(
            f"Price: "
            f"${listing.list_price:,.0f}"
        )

        print(
            f"Bedrooms: "
            f"{listing.bedrooms_total}"
        )

        print(
            f"Bathrooms: "
            f"{listing.bathrooms_total_integer}"
        )

        print(
            f"Living area: "
            f"{listing.living_area}"
        )

        remarks = (
            listing.public_remarks
            or ""
        )

        print(
            f"Text: "
            f"{remarks[:400]}"
        )

        validation = result[
            "comp_validation"
        ]

        print()
        print("Sold-Comp Validation")

        print(
            f"Status: "
            f"{validation['status']}"
        )

        if (
            validation["status"]
            == "validated"
        ):
            print(
                f"Match level: "
                f"{validation['match_level']}"
            )

            print(
                f"Comparable sales: "
                f"{validation['comp_count']}"
            )

            asking_ppsf = validation[
                "asking_price_per_sqft"
            ]

            comparable_ppsf = validation[
                "comparable_median_price_per_sqft"
            ]

            ratio = validation[
                "price_per_sqft_ratio"
            ]

            median_close = validation[
                "comparable_median_close_price"
            ]

            if asking_ppsf is not None:
                print(
                    f"Asking PPSF: "
                    f"${asking_ppsf:,.2f}"
                )

            if comparable_ppsf is not None:
                print(
                    f"Comparable median PPSF: "
                    f"${comparable_ppsf:,.2f}"
                )

            if ratio is not None:
                print(
                    f"Asking / comp PPSF ratio: "
                    f"{ratio:.3f}"
                )

            if median_close is not None:
                print(
                    f"Comparable median close price: "
                    f"${median_close:,.0f}"
                )

            print(
                f"Comparable value score: "
                f"{validation['comparable_value_score']:.2f}"
            )

            print(
                f"Comparable evidence quality: "
                f"{validation['comparable_quality_score']:.2f}"
            )

            for signal in validation[
                "signals"
            ]:
                print(
                    f"- {signal}"
                )

        else:
            print(
                "- Sold-comparable validation "
                "was unavailable."
            )

        print("-" * 100)


if __name__ == "__main__":
    main()