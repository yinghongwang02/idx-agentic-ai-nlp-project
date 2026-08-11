from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from src.providers.embedding_base import BaseEmbeddingProvider


class SemanticSearch:
    """FAISS-based semantic search over embedded MLS listings."""

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
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {self.index_path}"
            )

        return faiss.read_index(str(self.index_path))

    def _load_metadata(self) -> list[dict[str, Any]]:
        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"Metadata file not found: {self.metadata_path}"
            )

        metadata: list[dict[str, Any]] = []

        with self.metadata_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                if not line.strip():
                    continue

                metadata.append(json.loads(line))

        return metadata

    def _validate_alignment(self) -> None:
        if self.index.ntotal != len(self.metadata):
            raise RuntimeError(
                "FAISS index size does not match metadata count: "
                f"{self.index.ntotal} vs {len(self.metadata)}."
            )

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if not query or not query.strip():
            raise ValueError("Search query must not be empty.")

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")

        query_embedding = self.provider.embed_query(
            query.strip()
        )

        query_vector = np.asarray(
            [query_embedding],
            dtype=np.float32,
        )

        if query_vector.ndim != 2:
            raise RuntimeError(
                "Expected query embedding to form a 2D matrix."
            )

        if query_vector.shape[1] != self.index.d:
            raise RuntimeError(
                "Query embedding dimension does not match "
                f"FAISS index dimension: "
                f"{query_vector.shape[1]} vs {self.index.d}."
            )

        if not np.isfinite(query_vector).all():
            raise RuntimeError(
                "Query embedding contains NaN or infinite values."
            )

        query_vector = np.ascontiguousarray(
            query_vector
        )

        faiss.normalize_L2(query_vector)

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

            metadata = self.metadata[row_index]

            results.append(
                {
                    "score": float(score),
                    "embedding_row": int(row_index),
                    **metadata,
                }
            )

        return results