from __future__ import annotations

import argparse
import json
from pathlib import Path

import faiss

from src.embeddings.faiss_index import (
    build_cosine_index,
    load_embeddings,
    save_index,
)


DEFAULT_EMBEDDINGS_PATH = Path(
    "artifacts/embeddings/listing_embeddings.npy"
)

DEFAULT_METADATA_PATH = Path(
    "artifacts/embeddings/listing_metadata.jsonl"
)

DEFAULT_MANIFEST_PATH = Path(
    "artifacts/embeddings/embedding_manifest.json"
)

DEFAULT_INDEX_PATH = Path(
    "artifacts/embeddings/listing_embeddings.faiss"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a FAISS cosine-similarity index "
            "from listing embeddings."
        )
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

    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_INDEX_PATH,
    )

    return parser.parse_args()


def count_metadata_rows(
    metadata_path: Path,
) -> int:
    """Count aligned metadata records."""
    with metadata_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return sum(1 for line in file if line.strip())


def load_manifest(
    manifest_path: Path,
) -> dict:
    """Load embedding-generation metadata."""
    with manifest_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def validate_artifacts(
    embedding_count: int,
    metadata_path: Path,
    manifest_path: Path,
) -> None:
    """Validate embedding/metadata/manifest alignment."""
    metadata_count = count_metadata_rows(
        metadata_path
    )

    manifest = load_manifest(
        manifest_path
    )

    manifest_count = manifest.get(
        "listing_count"
    )

    if embedding_count != metadata_count:
        raise RuntimeError(
            "Embedding count does not match metadata count: "
            f"{embedding_count} vs {metadata_count}."
        )

    if embedding_count != manifest_count:
        raise RuntimeError(
            "Embedding count does not match manifest count: "
            f"{embedding_count} vs {manifest_count}."
        )


def main() -> None:
    args = parse_args()

    embeddings = load_embeddings(
        args.embeddings
    )

    print(
        f"Loaded embeddings: {embeddings.shape}"
    )

    validate_artifacts(
        embedding_count=embeddings.shape[0],
        metadata_path=args.metadata,
        manifest_path=args.manifest,
    )

    print(
        "Embedding, metadata, and manifest counts "
        "are aligned."
    )

    index = build_cosine_index(
        embeddings
    )

    print(
        f"Built FAISS index: "
        f"{index.ntotal} vectors, "
        f"dimension {index.d}"
    )

    save_index(
        index=index,
        output_path=args.output,
    )

    print(
        f"Saved FAISS index: {args.output}"
    )

    # Reload once to verify serialization.
    reloaded_index = faiss.read_index(
        str(args.output)
    )

    if reloaded_index.ntotal != index.ntotal:
        raise RuntimeError(
            "Reloaded FAISS index has an unexpected size."
        )

    if reloaded_index.d != index.d:
        raise RuntimeError(
            "Reloaded FAISS index has an unexpected dimension."
        )

    print(
        "FAISS index reload validation passed."
    )


if __name__ == "__main__":
    main()