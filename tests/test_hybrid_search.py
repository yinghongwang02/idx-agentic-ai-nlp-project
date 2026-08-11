import json
from pathlib import Path

import numpy as np
import pytest

from src.providers.embedding_base import BaseEmbeddingProvider
from src.schemas.listing_schema import ListingSchema
from src.search.hybrid_search import HybridSearch


class FakeEmbeddingProvider(BaseEmbeddingProvider):
    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        if text == "pool and views":
            return [1.0, 0.0]

        return [0.0, 1.0]

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return [
            self.embed_query(text)
            for text in texts
        ]


def make_listing(
    listing_key: str,
    city: str = "Irvine",
    price: float = 1_000_000,
) -> ListingSchema:
    return ListingSchema(
        listing_key=listing_key,
        unparsed_address=f"{listing_key} Main St",
        city=city,
        list_price=price,
    )


def build_test_artifacts(
    tmp_path: Path,
) -> tuple[Path, Path]:
    """
    Create three embeddings:

    listing 1 -> strongly matches [1, 0]
    listing 2 -> partially matches [1, 0]
    listing 3 -> matches [0, 1]
    """
    embeddings = np.array(
        [
            [1.0, 0.0],
            [0.8, 0.6],
            [0.0, 1.0],
        ],
        dtype=np.float32,
    )

    embeddings_path = tmp_path / "embeddings.npy"
    np.save(
        embeddings_path,
        embeddings,
    )

    metadata = [
        {
            "embedding_row": 0,
            "listing_id": "1",
        },
        {
            "embedding_row": 1,
            "listing_id": "2",
        },
        {
            "embedding_row": 2,
            "listing_id": "3",
        },
    ]

    metadata_path = tmp_path / "metadata.jsonl"

    with metadata_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        for record in metadata:
            file.write(
                json.dumps(record)
                + "\n"
            )

    return embeddings_path, metadata_path


def test_hybrid_search_ranks_semantic_candidate_first(
    tmp_path: Path,
) -> None:
    embeddings_path, metadata_path = (
        build_test_artifacts(tmp_path)
    )

    searcher = HybridSearch(
        provider=FakeEmbeddingProvider(),
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
    )

    candidates = [
        make_listing("1"),
        make_listing("2"),
        make_listing("3"),
    ]

    results = searcher.rerank(
        candidates=candidates,
        semantic_query="pool and views",
        top_k=3,
    )

    assert len(results) == 3

    assert results[0]["listing"].listing_key == "1"
    assert results[1]["listing"].listing_key == "2"
    assert results[2]["listing"].listing_key == "3"

    assert results[0]["semantic_score"] > results[1]["semantic_score"]
    assert results[1]["semantic_score"] > results[2]["semantic_score"]


def test_hybrid_search_preserves_structured_candidate_set(
    tmp_path: Path,
) -> None:
    embeddings_path, metadata_path = (
        build_test_artifacts(tmp_path)
    )

    searcher = HybridSearch(
        provider=FakeEmbeddingProvider(),
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
    )

    # Pretend structured SQL search only returned listings 2 and 3.
    candidates = [
        make_listing("2"),
        make_listing("3"),
    ]

    results = searcher.rerank(
        candidates=candidates,
        semantic_query="pool and views",
        top_k=5,
    )

    returned_ids = {
        result["listing"].listing_key
        for result in results
    }

    assert returned_ids == {"2", "3"}

    # Listing 1 has the best global semantic score,
    # but it must never enter the result because SQL did not
    # include it in the eligible candidate set.
    assert "1" not in returned_ids


def test_hybrid_search_skips_candidate_without_embedding(
    tmp_path: Path,
) -> None:
    embeddings_path, metadata_path = (
        build_test_artifacts(tmp_path)
    )

    searcher = HybridSearch(
        provider=FakeEmbeddingProvider(),
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
    )

    candidates = [
        make_listing("1"),
        make_listing("999"),
    ]

    results = searcher.rerank(
        candidates=candidates,
        semantic_query="pool and views",
        top_k=5,
    )

    assert len(results) == 1
    assert results[0]["listing"].listing_key == "1"


def test_hybrid_search_limits_top_k(
    tmp_path: Path,
) -> None:
    embeddings_path, metadata_path = (
        build_test_artifacts(tmp_path)
    )

    searcher = HybridSearch(
        provider=FakeEmbeddingProvider(),
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
    )

    candidates = [
        make_listing("1"),
        make_listing("2"),
        make_listing("3"),
    ]

    results = searcher.rerank(
        candidates=candidates,
        semantic_query="pool and views",
        top_k=2,
    )

    assert len(results) == 2


def test_hybrid_search_rejects_empty_semantic_query(
    tmp_path: Path,
) -> None:
    embeddings_path, metadata_path = (
        build_test_artifacts(tmp_path)
    )

    searcher = HybridSearch(
        provider=FakeEmbeddingProvider(),
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
    )

    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        searcher.rerank(
            candidates=[make_listing("1")],
            semantic_query="   ",
        )


def test_hybrid_search_returns_empty_for_no_candidates(
    tmp_path: Path,
) -> None:
    embeddings_path, metadata_path = (
        build_test_artifacts(tmp_path)
    )

    searcher = HybridSearch(
        provider=FakeEmbeddingProvider(),
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
    )

    results = searcher.rerank(
        candidates=[],
        semantic_query="pool and views",
    )

    assert results == []


def test_hybrid_search_validates_metadata_alignment(
    tmp_path: Path,
) -> None:
    embeddings_path, metadata_path = (
        build_test_artifacts(tmp_path)
    )

    metadata_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "embedding_row": 0,
                        "listing_id": "1",
                    }
                ),
                json.dumps(
                    {
                        "embedding_row": 99,
                        "listing_id": "2",
                    }
                ),
                json.dumps(
                    {
                        "embedding_row": 2,
                        "listing_id": "3",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        RuntimeError,
        match="Metadata embedding_row is not aligned",
    ):
        HybridSearch(
            provider=FakeEmbeddingProvider(),
            embeddings_path=embeddings_path,
            metadata_path=metadata_path,
        )