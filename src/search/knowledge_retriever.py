from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from src.providers.embedding_base import BaseEmbeddingProvider


class KnowledgeRetriever:
    """FAISS-based semantic retrieval over knowledge-document chunks."""

    def __init__(
        self,
        provider: BaseEmbeddingProvider,
        index_path: Path,
        metadata_path: Path,
    ) -> None:
        self.provider = provider
        self.index_path = index_path
        self.metadata_path = metadata_path

        self.index = self._load_index()
        self.metadata = self._load_metadata()

        self._validate_alignment()

    def _load_index(self) -> faiss.Index:
        """Load the persisted knowledge FAISS index."""

        if not self.index_path.exists():
            raise FileNotFoundError(
                f"Knowledge FAISS index not found: "
                f"{self.index_path}"
            )

        return faiss.read_index(
            str(self.index_path)
        )

    def _load_metadata(
        self,
    ) -> list[dict[str, Any]]:
        """Load metadata aligned with FAISS index rows."""

        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"Knowledge metadata not found: "
                f"{self.metadata_path}"
            )

        metadata: list[dict[str, Any]] = []

        with self.metadata_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                if not line.strip():
                    continue

                metadata.append(
                    json.loads(line)
                )

        if not metadata:
            raise RuntimeError(
                "Knowledge metadata file is empty."
            )

        return metadata

    def _validate_alignment(self) -> None:
        """
        Validate one-to-one alignment between FAISS rows
        and knowledge metadata records.
        """

        if self.index.ntotal != len(self.metadata):
            raise RuntimeError(
                "FAISS index size does not match "
                "knowledge metadata count: "
                f"{self.index.ntotal} vs "
                f"{len(self.metadata)}."
            )

        for expected_row, record in enumerate(
            self.metadata
        ):
            metadata_row = record.get(
                "embedding_row"
            )

            if metadata_row != expected_row:
                raise RuntimeError(
                    "Knowledge metadata embedding_row "
                    "is not aligned with FAISS row: "
                    f"expected {expected_row}, "
                    f"received {metadata_row}."
                )

    def search(
        self,
        query: str,
        top_k: int = 4,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the most relevant knowledge chunks
        for a natural-language question.
        """

        if not query or not query.strip():
            raise ValueError(
                "Knowledge search query must not be empty."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        if self.index.ntotal == 0:
            return []

        query_embedding = (
            self.provider.embed_query(
                query.strip()
            )
        )

        query_vector = np.asarray(
            [query_embedding],
            dtype=np.float32,
        )

        if query_vector.ndim != 2:
            raise RuntimeError(
                "Expected query embedding "
                "to form a 2D matrix."
            )

        if query_vector.shape[1] != self.index.d:
            raise RuntimeError(
                "Query embedding dimension does not "
                "match knowledge FAISS index dimension: "
                f"{query_vector.shape[1]} vs "
                f"{self.index.d}."
            )

        if not np.isfinite(
            query_vector
        ).all():
            raise RuntimeError(
                "Query embedding contains "
                "NaN or infinite values."
            )

        query_vector = np.ascontiguousarray(
            query_vector
        )

        faiss.normalize_L2(
            query_vector
        )

        effective_top_k = min(
            top_k,
            self.index.ntotal,
        )

        scores, indices = self.index.search(
            query_vector,
            effective_top_k,
        )

        results: list[dict[str, Any]] = []

        for score, row_index in zip(
            scores[0],
            indices[0],
        ):
            if row_index < 0:
                continue

            metadata = self.metadata[
                int(row_index)
            ]

            results.append(
                {
                    "score": float(score),
                    **metadata,
                }
            )

        return results