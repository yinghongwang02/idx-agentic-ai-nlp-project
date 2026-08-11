import json
from pathlib import Path

import faiss
import numpy as np
import pytest

from src.providers.embedding_base import BaseEmbeddingProvider
from src.search.semantic_search import SemanticSearch


class FakeEmbeddingProvider(BaseEmbeddingProvider):
    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        if text == "ranch":
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


def build_test_artifacts(
    tmp_path: Path,
) -> tuple[Path, Path]:
    embeddings = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
        ],
        dtype=np.float32,
    )

    faiss.normalize_L2(embeddings)

    index = faiss.IndexFlatIP(2)
    index.add(embeddings)

    index_path = tmp_path / "test.faiss"

    faiss.write_index(
        index,
        str(index_path),
    )

    metadata_path = tmp_path / "metadata.jsonl"

    metadata = [
        {
            "embedding_row": 0,
            "listing_id": "ranch-1",
            "embedding_text": (
                "Ranch with farmland and mountain views."
            ),
        },
        {
            "embedding_row": 1,
            "listing_id": "condo-1",
            "embedding_text": (
                "Modern downtown condominium."
            ),
        },
    ]

    with metadata_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        for record in metadata:
            file.write(
                json.dumps(record)
                + "\n"
            )

    return index_path, metadata_path


def test_semantic_search_returns_expected_listing(
    tmp_path: Path,
) -> None:
    index_path, metadata_path = (
        build_test_artifacts(tmp_path)
    )

    searcher = SemanticSearch(
        provider=FakeEmbeddingProvider(),
        index_path=index_path,
        metadata_path=metadata_path,
    )

    results = searcher.search(
        "ranch",
        top_k=1,
    )

    assert len(results) == 1
    assert results[0]["listing_id"] == "ranch-1"
    assert results[0]["embedding_row"] == 0
    assert results[0]["score"] > 0.99


def test_semantic_search_rejects_empty_query(
    tmp_path: Path,
) -> None:
    index_path, metadata_path = (
        build_test_artifacts(tmp_path)
    )

    searcher = SemanticSearch(
        provider=FakeEmbeddingProvider(),
        index_path=index_path,
        metadata_path=metadata_path,
    )

    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        searcher.search("   ")


def test_semantic_search_limits_top_k(
    tmp_path: Path,
) -> None:
    index_path, metadata_path = (
        build_test_artifacts(tmp_path)
    )

    searcher = SemanticSearch(
        provider=FakeEmbeddingProvider(),
        index_path=index_path,
        metadata_path=metadata_path,
    )

    results = searcher.search(
        "ranch",
        top_k=10,
    )

    assert len(results) == 2


def test_semantic_search_validates_alignment(
    tmp_path: Path,
) -> None:
    index_path, metadata_path = (
        build_test_artifacts(tmp_path)
    )

    metadata_path.write_text(
        json.dumps(
            {
                "embedding_row": 0,
                "listing_id": "only-one",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        RuntimeError,
        match="does not match metadata count",
    ):
        SemanticSearch(
            provider=FakeEmbeddingProvider(),
            index_path=index_path,
            metadata_path=metadata_path,
        )