from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from src.schemas.listing_schema import ListingSchema


class SimilarListingRetriever:
    """
    Retrieve active listings similar to a target listing.

    The hybrid score follows the following design:

        structured similarity: 60 points
        semantic similarity:   40 points

    Structured similarity considers:
        - price similarity
        - bedroom match
        - city match
        - living-area similarity

    Semantic similarity uses cosine similarity between the
    target listing embedding and candidate listing embeddings.

    Candidate eligibility additionally requires matching
    property types when both target and candidate property
    types are available.

    This component performs listing-to-listing retrieval only.
    It does not replace the existing RecommendationAgent or
    PropertyAnalysisSubgraph.
    """

    STRUCTURED_MAX_SCORE = 60.0
    SEMANTIC_MAX_SCORE = 40.0

    def __init__(
        self,
        embeddings_path: Path,
        metadata_path: Path,
    ) -> None:
        self.embeddings_path = embeddings_path
        self.metadata_path = metadata_path

        self.embeddings = self._load_embeddings()
        self.metadata = self._load_metadata()

        self._validate_alignment()

        self.listing_id_to_row = (
            self._build_listing_id_lookup()
        )

        # Precompute vector norms once so repeated recommendation
        # requests do not recalculate every candidate norm.
        self.embedding_norms = np.linalg.norm(
            self.embeddings,
            axis=1,
        ).astype(
            np.float32,
            copy=False,
        )

    def _load_embeddings(self) -> np.ndarray:
        if not self.embeddings_path.exists():
            raise FileNotFoundError(
                f"Embedding file not found: "
                f"{self.embeddings_path}"
            )

        embeddings = np.load(
            self.embeddings_path
        )

        if embeddings.ndim != 2:
            raise RuntimeError(
                "Expected a 2D embedding matrix, "
                f"received shape {embeddings.shape}."
            )

        if embeddings.shape[0] == 0:
            raise RuntimeError(
                "Embedding matrix must not be empty."
            )

        embeddings = embeddings.astype(
            np.float32,
            copy=False,
        )

        if not np.isfinite(
            embeddings
        ).all():
            raise RuntimeError(
                "Embedding matrix contains NaN "
                "or infinite values."
            )

        return np.ascontiguousarray(
            embeddings
        )

    def _load_metadata(
        self,
    ) -> list[dict[str, Any]]:
        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"Metadata file not found: "
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

        return metadata

    def _validate_alignment(self) -> None:
        if (
            self.embeddings.shape[0]
            != len(self.metadata)
        ):
            raise RuntimeError(
                "Embedding row count does not match "
                "metadata count: "
                f"{self.embeddings.shape[0]} vs "
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
                    "Metadata embedding_row is not "
                    "aligned with the embedding matrix: "
                    f"expected {expected_row}, "
                    f"received {metadata_row}."
                )

    def _build_listing_id_lookup(
        self,
    ) -> dict[str, int]:
        lookup: dict[str, int] = {}

        for row_index, record in enumerate(
            self.metadata
        ):
            listing_id = record.get(
                "listing_id"
            )

            if listing_id is None:
                continue

            normalized_id = str(
                listing_id
            )

            if normalized_id in lookup:
                raise RuntimeError(
                    "Duplicate listing_id in embedding "
                    f"metadata: {normalized_id}"
                )

            lookup[normalized_id] = row_index

        return lookup

    @staticmethod
    def _safe_float(
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(
        value: Any,
    ) -> int | None:
        if value is None:
            return None

        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_property_type(
        value: Any,
    ) -> str:
        """
        Normalize MLS property-type values for eligibility checks.

        Examples:
            "Condominium" -> "condominium"
            " SingleFamilyResidence " -> "singlefamilyresidence"
            None -> ""
        """
        return (
            str(value or "")
            .strip()
            .lower()
        )

    @classmethod
    def _property_types_are_compatible(
        cls,
        target: dict[str, Any],
        candidate: dict[str, Any],
    ) -> bool:
        """
        Require the same property type when both values exist.

        Missing property-type data does not automatically remove
        a candidate, preventing data-quality gaps from acting as
        hard exclusions.
        """
        target_property_type = (
            cls._normalize_property_type(
                target.get(
                    "property_type"
                )
            )
        )

        candidate_property_type = (
            cls._normalize_property_type(
                candidate.get(
                    "property_type"
                )
            )
        )

        if (
            target_property_type
            and candidate_property_type
        ):
            return (
                target_property_type
                == candidate_property_type
            )

        return True

    @classmethod
    def _structured_similarity_score(
        cls,
        target: dict[str, Any],
        candidate: dict[str, Any],
    ) -> float:
        """
        Structured similarity: 

        Maximum:
            price      20
            bedrooms   15
            city       15
            sqft       10

        Total          60

        Property type is handled separately as a candidate
        eligibility guardrail and therefore does not change
        the original 60-point structured scoring policy.
        """
        score = 0.0

        target_price = cls._safe_float(
            target.get("list_price")
        )
        candidate_price = cls._safe_float(
            candidate.get("list_price")
        )

        if (
            target_price is not None
            and candidate_price is not None
        ):
            price_difference = abs(
                target_price
                - candidate_price
            )

            if price_difference < 50_000:
                score += 20.0
            elif price_difference < 150_000:
                score += 12.0
            elif price_difference < 300_000:
                score += 5.0

        target_bedrooms = cls._safe_int(
            target.get("bedrooms")
        )
        candidate_bedrooms = cls._safe_int(
            candidate.get("bedrooms")
        )

        if (
            target_bedrooms is not None
            and candidate_bedrooms is not None
            and target_bedrooms
            == candidate_bedrooms
        ):
            score += 15.0

        target_city = str(
            target.get("city") or ""
        ).strip().lower()

        candidate_city = str(
            candidate.get("city") or ""
        ).strip().lower()

        if (
            target_city
            and candidate_city
            and target_city
            == candidate_city
        ):
            score += 15.0

        target_sqft = cls._safe_float(
            target.get("living_area")
        )
        candidate_sqft = cls._safe_float(
            candidate.get("living_area")
        )

        if (
            target_sqft is not None
            and candidate_sqft is not None
        ):
            sqft_difference = abs(
                target_sqft
                - candidate_sqft
            )

            if sqft_difference < 300:
                score += 10.0
            elif sqft_difference < 700:
                score += 5.0

        return score

    def _semantic_scores(
        self,
        target_row: int,
    ) -> np.ndarray:
        """
        Calculate cosine similarity between one target listing
        and every listing in the corpus.

        cosine(a, b) =
            dot(a, b) / (||a|| * ||b||)
        """
        target_vector = self.embeddings[
            target_row
        ]

        target_norm = float(
            self.embedding_norms[
                target_row
            ]
        )

        if target_norm <= 0:
            raise RuntimeError(
                "Target listing embedding has "
                "zero L2 norm."
            )

        dot_products = (
            self.embeddings
            @ target_vector
        )

        denominators = (
            self.embedding_norms
            * target_norm
        )

        scores = np.zeros(
            self.embeddings.shape[0],
            dtype=np.float32,
        )

        valid_mask = denominators > 0

        scores[valid_mask] = (
            dot_products[valid_mask]
            / denominators[valid_mask]
        )

        return scores

    def _metadata_to_listing(
        self,
        record: dict[str, Any],
    ) -> ListingSchema:
        listing_id = str(
            record["listing_id"]
        )

        return ListingSchema(
            listing_key=listing_id,
            listing_id=listing_id,
            unparsed_address=(
                record.get("address")
                or "Address unavailable"
            ),
            city=(
                record.get("city")
                or ""
            ),
            postal_code=(
                str(record["zip"])
                if record.get("zip")
                is not None
                else None
            ),
            property_sub_type=(
                record.get(
                    "property_type"
                )
            ),
            list_price=float(
                record.get(
                    "list_price"
                )
                or 0.0
            ),
            bedrooms_total=(
                self._safe_int(
                    record.get(
                        "bedrooms"
                    )
                )
            ),
            bathrooms_total_integer=(
                self._safe_int(
                    record.get(
                        "bathrooms"
                    )
                )
            ),
            living_area=(
                self._safe_float(
                    record.get(
                        "living_area"
                    )
                )
            ),
            association_fee=(
                self._safe_float(
                    record.get(
                        "association_fee"
                    )
                )
            ),
            days_on_market=(
                self._safe_int(
                    record.get(
                        "days_on_market"
                    )
                )
            ),
            public_remarks=(
                record.get(
                    "embedding_text"
                )
            ),
        )

    def recommend_similar(
        self,
        target_listing_id: str,
        top_k: int = 5,
        candidate_pool_size: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return listings most similar to one target listing.

        Candidate rules:
            1. Exclude the target itself.
            2. Require matching property type when both target
               and candidate property types are available.
            3. Rank remaining candidates with the 
               60/40 structured-semantic hybrid score.
        """
        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        if (
            candidate_pool_size is not None
            and candidate_pool_size <= 0
        ):
            raise ValueError(
                "candidate_pool_size must be "
                "greater than zero."
            )

        normalized_target_id = str(
            target_listing_id
        )

        target_row = (
            self.listing_id_to_row.get(
                normalized_target_id
            )
        )

        if target_row is None:
            raise ValueError(
                "Target listing is not present "
                "in the embedding corpus: "
                f"{normalized_target_id}"
            )

        target_metadata = self.metadata[
            target_row
        ]

        semantic_scores = (
            self._semantic_scores(
                target_row
            )
        )

        results: list[
            dict[str, Any]
        ] = []

        for row_index, candidate in enumerate(
            self.metadata
        ):
            # Never recommend the target listing itself.
            if row_index == target_row:
                continue

            # Candidate eligibility guardrail:
            #
            # If both listings expose a property type, only compare
            # listings of the same type. This prevents a structurally
            # similar condominium from being recommended for a
            # single-family target, while preserving candidates whose
            # type is missing because of incomplete MLS metadata.
            if not self._property_types_are_compatible(
                target=target_metadata,
                candidate=candidate,
            ):
                continue

            structured_score = (
                self._structured_similarity_score(
                    target=target_metadata,
                    candidate=candidate,
                )
            )

            semantic_similarity = float(
                semantic_scores[
                    row_index
                ]
            )

            # Listing embeddings normally produce positive cosine
            # similarity, but clamp to [0, 1] before converting the
            # similarity into the 40-point component.
            bounded_semantic_similarity = max(
                0.0,
                min(
                    1.0,
                    semantic_similarity,
                ),
            )

            semantic_score = (
                bounded_semantic_similarity
                * self.SEMANTIC_MAX_SCORE
            )

            hybrid_score = (
                structured_score
                + semantic_score
            )

            results.append(
                {
                    "listing": (
                        self._metadata_to_listing(
                            candidate
                        )
                    ),
                    "hybrid_similarity_score": round(
                        hybrid_score,
                        4,
                    ),
                    "structured_similarity_score": round(
                        structured_score,
                        4,
                    ),
                    "semantic_similarity": round(
                        semantic_similarity,
                        4,
                    ),
                    "semantic_similarity_score": round(
                        semantic_score,
                        4,
                    ),
                    "embedding_row": row_index,
                }
            )

        results.sort(
            key=lambda result: (
                -result[
                    "hybrid_similarity_score"
                ],
                result[
                    "listing"
                ].listing_key,
            )
        )

        if candidate_pool_size is not None:
            results = results[
                :candidate_pool_size
            ]

        return results[:top_k]