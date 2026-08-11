from pathlib import Path

import faiss
import numpy as np

from src.embeddings.faiss_index import (
    build_cosine_index,
    load_embeddings,
    load_index,
    save_index,
)


def test_build_cosine_index() -> None:
    embeddings = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
        ],
        dtype=np.float32,
    )

    index = build_cosine_index(
        embeddings
    )

    assert index.ntotal == 3
    assert index.d == 2


def test_cosine_index_returns_expected_neighbor() -> None:
    embeddings = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
        ],
        dtype=np.float32,
    )

    index = build_cosine_index(
        embeddings
    )

    query = np.array(
        [[1.0, 0.0]],
        dtype=np.float32,
    )

    faiss.normalize_L2(query)

    scores, indices = index.search(
        query,
        1,
    )

    assert indices[0][0] == 0
    assert scores[0][0] > 0.99


def test_build_cosine_index_does_not_modify_input() -> None:
    embeddings = np.array(
        [
            [3.0, 4.0],
        ],
        dtype=np.float32,
    )

    original = embeddings.copy()

    build_cosine_index(
        embeddings
    )

    np.testing.assert_array_equal(
        embeddings,
        original,
    )


def test_save_and_reload_index(
    tmp_path: Path,
) -> None:
    embeddings = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
        ],
        dtype=np.float32,
    )

    index = build_cosine_index(
        embeddings
    )

    output_path = (
        tmp_path / "test.faiss"
    )

    save_index(
        index,
        output_path,
    )

    loaded = load_index(
        output_path
    )

    assert loaded.ntotal == 2
    assert loaded.d == 2