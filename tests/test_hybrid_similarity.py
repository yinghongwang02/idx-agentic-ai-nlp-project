import json
from pathlib import Path

import numpy as np
import pytest

from src.recommendation.hybrid_similarity import (
    SimilarListingRetriever,
)


def build_test_artifacts(
    tmp_path: Path,
) -> tuple[Path, Path]:
    embeddings = np.array(
        [
            # target
            [1.0, 0.0],

            # Strong semantic + strong structured match
            [0.95, 0.05],

            # Weak semantic but same structured attributes
            [0.20, 0.98],

            # Strong semantic but weak structured attributes
            [0.90, 0.10],
        ],
        dtype=np.float32,
    )

    embeddings_path = (
        tmp_path / "embeddings.npy"
    )

    np.save(
        embeddings_path,
        embeddings,
    )

    metadata = [
        {
            "embedding_row": 0,
            "listing_id": "TARGET",
            "address": "1 Target St",
            "city": "Irvine",
            "zip": "92618",
            "list_price": 1_000_000,
            "bedrooms": 3,
            "bathrooms": 2,
            "living_area": 1800,
            "property_type": (
                "SingleFamilyResidence"
            ),
            "embedding_text": (
                "Modern Irvine home."
            ),
        },
        {
            "embedding_row": 1,
            "listing_id": "BEST",
            "address": "2 Best St",
            "city": "Irvine",
            "zip": "92618",
            "list_price": 1_030_000,
            "bedrooms": 3,
            "bathrooms": 2,
            "living_area": 1900,
            "property_type": (
                "SingleFamilyResidence"
            ),
            "embedding_text": (
                "Modern Irvine home."
            ),
        },
        {
            "embedding_row": 2,
            "listing_id": "STRUCTURED",
            "address": "3 Structured St",
            "city": "Irvine",
            "zip": "92618",
            "list_price": 1_020_000,
            "bedrooms": 3,
            "bathrooms": 2,
            "living_area": 1850,
            "property_type": (
                "SingleFamilyResidence"
            ),
            "embedding_text": (
                "Traditional property."
            ),
        },
        {
            "embedding_row": 3,
            "listing_id": "SEMANTIC",
            "address": "4 Semantic St",
            "city": "Los Angeles",
            "zip": "90001",
            "list_price": 1_500_000,
            "bedrooms": 5,
            "bathrooms": 4,
            "living_area": 3200,
            "property_type": (
                "SingleFamilyResidence"
            ),
            "embedding_text": (
                "Modern architectural home."
            ),
        },
    ]

    metadata_path = (
        tmp_path / "metadata.jsonl"
    )

    with metadata_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        for record in metadata:
            file.write(
                json.dumps(record)
                + "\n"
            )

    return (
        embeddings_path,
        metadata_path,
    )


def test_recommends_best_hybrid_match_first(
    tmp_path: Path,
) -> None:
    (
        embeddings_path,
        metadata_path,
    ) = build_test_artifacts(
        tmp_path
    )

    retriever = SimilarListingRetriever(
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
    )

    results = retriever.recommend_similar(
        target_listing_id="TARGET",
        top_k=3,
    )

    assert (
        results[0]["listing"].listing_key
        == "BEST"
    )

    assert (
        results[0][
            "structured_similarity_score"
        ]
        == 60.0
    )

    assert (
        results[0][
            "semantic_similarity"
        ]
        > 0.99
    )


def test_excludes_target_listing(
    tmp_path: Path,
) -> None:
    (
        embeddings_path,
        metadata_path,
    ) = build_test_artifacts(
        tmp_path
    )

    retriever = SimilarListingRetriever(
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
    )

    results = retriever.recommend_similar(
        target_listing_id="TARGET",
        top_k=10,
    )

    returned_ids = {
        result["listing"].listing_key
        for result in results
    }

    assert "TARGET" not in returned_ids


def test_hybrid_score_combines_structured_and_semantic(
    tmp_path: Path,
) -> None:
    (
        embeddings_path,
        metadata_path,
    ) = build_test_artifacts(
        tmp_path
    )

    retriever = SimilarListingRetriever(
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
    )

    result = retriever.recommend_similar(
        target_listing_id="TARGET",
        top_k=1,
    )[0]

    expected = (
        result[
            "structured_similarity_score"
        ]
        + result[
            "semantic_similarity_score"
        ]
    )

    assert (
        result[
            "hybrid_similarity_score"
        ]
        == pytest.approx(
            expected,
            abs=1e-4,
        )
    )


def test_missing_target_listing_raises(
    tmp_path: Path,
) -> None:
    (
        embeddings_path,
        metadata_path,
    ) = build_test_artifacts(
        tmp_path
    )

    retriever = SimilarListingRetriever(
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
    )

    with pytest.raises(
        ValueError,
        match="not present",
    ):
        retriever.recommend_similar(
            target_listing_id="MISSING"
        )


def test_rejects_invalid_top_k(
    tmp_path: Path,
) -> None:
    (
        embeddings_path,
        metadata_path,
    ) = build_test_artifacts(
        tmp_path
    )

    retriever = SimilarListingRetriever(
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
    )

    with pytest.raises(
        ValueError,
        match="top_k",
    ):
        retriever.recommend_similar(
            target_listing_id="TARGET",
            top_k=0,
        )


def test_filters_different_property_type(
    tmp_path: Path,
) -> None:
    (
        embeddings_path,
        metadata_path,
    ) = build_test_artifacts(
        tmp_path
    )

    retriever = SimilarListingRetriever(
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
    )

    results = retriever.recommend_similar(
        target_listing_id="TARGET",
        top_k=10,
    )

    returned_ids = {
        result["listing"].listing_key
        for result in results
    }

    assert "WRONG-TYPE" not in returned_ids