from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from src.providers.embedding_base import BaseEmbeddingProvider
from src.schemas.listing_schema import ListingSchema


class HybridSearch:
    """
    Semantic reranker for structured MLS search candidates.

    Structured search is responsible for deterministic hard constraints
    such as city, price, bedrooms, bathrooms, and property type.

    HybridSearch then reranks only those eligible candidates using
    embedding similarity against a semantic preference query.
    """

    def __init__(
        self,
        provider: BaseEmbeddingProvider,
        embeddings_path: Path,
        metadata_path: Path,
    ) -> None:
        self.provider = provider
        self.embeddings_path = embeddings_path
        self.metadata_path = metadata_path

        self.embeddings = self._load_embeddings()
        self.metadata = self._load_metadata()

        self._validate_artifacts()

        self.listing_id_to_row = self._build_listing_id_lookup()

    def _load_embeddings(self) -> np.ndarray:
        if not self.embeddings_path.exists():
            raise FileNotFoundError(
                f"Embedding file not found: {self.embeddings_path}"
            )

        embeddings = np.load(self.embeddings_path)

        if embeddings.ndim != 2:
            raise RuntimeError(
                "Expected a 2D embedding matrix, "
                f"received shape {embeddings.shape}."
            )

        if embeddings.shape[0] == 0:
            raise RuntimeError(
                "Embedding matrix must not be empty."
            )

        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(
                np.float32,
                copy=False,
            )

        if not np.isfinite(embeddings).all():
            raise RuntimeError(
                "Embedding matrix contains NaN or infinite values."
            )

        return np.ascontiguousarray(embeddings)

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

                metadata.append(
                    json.loads(line)
                )

        return metadata

    def _validate_artifacts(self) -> None:
        if self.embeddings.shape[0] != len(self.metadata):
            raise RuntimeError(
                "Embedding row count does not match metadata count: "
                f"{self.embeddings.shape[0]} vs {len(self.metadata)}."
            )

        for expected_row, record in enumerate(self.metadata):
            metadata_row = record.get("embedding_row")

            if metadata_row != expected_row:
                raise RuntimeError(
                    "Metadata embedding_row is not aligned with "
                    "embedding matrix position: "
                    f"expected {expected_row}, received {metadata_row}."
                )

    def _build_listing_id_lookup(self) -> dict[str, int]:
        """
        Map MLS listing IDs to embedding rows.

        String normalization avoids mismatches caused by one side
        representing an ID as an int and the other as a string.
        """
        lookup: dict[str, int] = {}

        for row_index, record in enumerate(self.metadata):
            listing_id = record.get("listing_id")

            if listing_id is None:
                continue

            normalized_id = str(listing_id)

            if normalized_id in lookup:
                raise RuntimeError(
                    f"Duplicate listing_id in embedding metadata: "
                    f"{normalized_id}"
                )

            lookup[normalized_id] = row_index

        return lookup

    def _build_query_vector(
        self,
        semantic_query: str,
    ) -> np.ndarray:
        if not semantic_query or not semantic_query.strip():
            raise ValueError(
                "Semantic query must not be empty."
            )

        query_embedding = self.provider.embed_query(
            semantic_query.strip()
        )

        query_vector = np.asarray(
            query_embedding,
            dtype=np.float32,
        )

        if query_vector.ndim != 1:
            raise RuntimeError(
                "Expected a 1D query embedding vector, "
                f"received shape {query_vector.shape}."
            )

        if query_vector.shape[0] != self.embeddings.shape[1]:
            raise RuntimeError(
                "Query embedding dimension does not match "
                "listing embedding dimension: "
                f"{query_vector.shape[0]} vs "
                f"{self.embeddings.shape[1]}."
            )

        if not np.isfinite(query_vector).all():
            raise RuntimeError(
                "Query embedding contains NaN or infinite values."
            )

        norm = np.linalg.norm(query_vector)

        if norm == 0:
            raise RuntimeError(
                "Query embedding has zero L2 norm."
            )

        return query_vector / norm

    def _get_candidate_embedding_rows(
        self,
        candidates: list[ListingSchema],
    ) -> tuple[list[ListingSchema], list[int]]:
        matched_candidates: list[ListingSchema] = []
        embedding_rows: list[int] = []

        for candidate in candidates:
            listing_key = candidate.listing_key

            if listing_key is None:
                continue

            row_index = self.listing_id_to_row.get(
                str(listing_key)
            )

            if row_index is None:
                continue

            matched_candidates.append(candidate)
            embedding_rows.append(row_index)

        return matched_candidates, embedding_rows

    def rerank(
        self,
        candidates: list[ListingSchema],
        semantic_query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Rerank structured-search candidates by cosine similarity.

        Returns only candidates that exist in the embedding artifacts.
        """
        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        if not candidates:
            return []

        query_vector = self._build_query_vector(
            semantic_query
        )

        matched_candidates, embedding_rows = (
            self._get_candidate_embedding_rows(
                candidates
            )
        )

        if not matched_candidates:
            return []

        candidate_embeddings = self.embeddings[
            embedding_rows
        ].copy()

        norms = np.linalg.norm(
            candidate_embeddings,
            axis=1,
            keepdims=True,
        )

        valid_mask = norms[:, 0] > 0

        if not valid_mask.any():
            return []

        candidate_embeddings = candidate_embeddings[
            valid_mask
        ]
        norms = norms[valid_mask]

        matched_candidates = [
            candidate
            for candidate, is_valid in zip(
                matched_candidates,
                valid_mask,
            )
            if is_valid
        ]

        embedding_rows = [
            row_index
            for row_index, is_valid in zip(
                embedding_rows,
                valid_mask,
            )
            if is_valid
        ]

        normalized_candidate_embeddings = (
            candidate_embeddings / norms
        )

        scores = (
            normalized_candidate_embeddings
            @ query_vector
        )

        ranked_indices = np.argsort(scores)[::-1]

        effective_top_k = min(
            top_k,
            len(ranked_indices),
        )

        results: list[dict[str, Any]] = []

        for rank_index in ranked_indices[:effective_top_k]:
            candidate = matched_candidates[
                int(rank_index)
            ]
            embedding_row = embedding_rows[
                int(rank_index)
            ]
            score = scores[int(rank_index)]

            results.append(
                {
                    "listing": candidate,
                    "semantic_score": float(score),
                    "embedding_row": int(embedding_row),
                }
            )

        return results