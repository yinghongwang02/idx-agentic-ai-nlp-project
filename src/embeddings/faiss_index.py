from __future__ import annotations

from pathlib import Path

import faiss
import numpy as np


def load_embeddings(
    embeddings_path: Path,
) -> np.ndarray:
    """Load and validate an embedding matrix."""
    embeddings = np.load(embeddings_path)

    if embeddings.ndim != 2:
        raise ValueError(
            "Expected a 2D embedding matrix, "
            f"received shape {embeddings.shape}."
        )

    if embeddings.shape[0] == 0:
        raise ValueError("Embedding matrix must not be empty.")

    if embeddings.dtype != np.float32:
        embeddings = embeddings.astype(
            np.float32,
            copy=False,
        )

    if not np.isfinite(embeddings).all():
        raise ValueError(
            "Embedding matrix contains NaN or infinite values."
        )

    return np.ascontiguousarray(embeddings)


def build_cosine_index(
    embeddings: np.ndarray,
) -> faiss.IndexFlatIP:
    """
    Build an exact FAISS cosine-similarity index.

    Cosine similarity is implemented by L2-normalizing vectors
    and using inner-product search.
    """
    normalized_embeddings = embeddings.copy()

    faiss.normalize_L2(normalized_embeddings)

    dimension = normalized_embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)
    index.add(normalized_embeddings)

    if index.ntotal != normalized_embeddings.shape[0]:
        raise RuntimeError(
            "FAISS index size does not match embedding row count."
        )

    return index


def save_index(
    index: faiss.Index,
    output_path: Path,
) -> None:
    """Persist a FAISS index to disk."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    faiss.write_index(
        index,
        str(output_path),
    )


def load_index(
    index_path: Path,
) -> faiss.Index:
    """Load a persisted FAISS index."""
    if not index_path.exists():
        raise FileNotFoundError(
            f"FAISS index not found: {index_path}"
        )

    return faiss.read_index(
        str(index_path)
    )