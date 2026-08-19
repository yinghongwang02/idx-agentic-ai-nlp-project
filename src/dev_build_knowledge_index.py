from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from src.config.settings import settings
from src.providers.embedding_base import BaseEmbeddingProvider
from src.providers.factory import get_embedding_provider
from src.embeddings.faiss_index import build_cosine_index, save_index
from src.embeddings.knowledge_chunker import (
    KnowledgeChunk,
    chunk_text,
)

from src.knowledge.loader import (
    KnowledgeDocument,
    load_markdown_document,
    load_pdf_document,
)

DEFAULT_MODEL = settings.openai_embedding_model
DEFAULT_BATCH_SIZE = 50
DEFAULT_CHUNK_SIZE = 600
DEFAULT_OVERLAP = 100

DEFAULT_MAPPING_PATH = Path("docs/mls_field_mapping.md")
DEFAULT_HANDBOOK_PATH = Path("data/knowledge/handbook.pdf")
DEFAULT_OUTPUT_DIR = Path("artifacts/knowledge")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a FAISS knowledge index from project "
            "documentation for Week 8 RAG."
        )
    )

    parser.add_argument(
        "--mapping-path",
        type=Path,
        default=DEFAULT_MAPPING_PATH,
        help="Path to the project-maintained MLS field mapping.",
    )

    parser.add_argument(
        "--handbook-path",
        type=Path,
        default=DEFAULT_HANDBOOK_PATH,
        help="Path to the local internship handbook PDF.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory used to store knowledge-index artifacts.",
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Embedding model.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of knowledge chunks per embedding request.",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Maximum chunk size in characters.",
    )

    parser.add_argument(
        "--overlap",
        type=int,
        default=DEFAULT_OVERLAP,
        help="Character overlap between consecutive chunks.",
    )

    args = parser.parse_args()

    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than zero.")

    if args.chunk_size <= 0:
        parser.error("--chunk-size must be greater than zero.")

    if args.overlap < 0:
        parser.error("--overlap must not be negative.")

    if args.overlap >= args.chunk_size:
        parser.error(
            "--overlap must be smaller than --chunk-size."
        )

    return args


def load_knowledge_documents(
    mapping_path: Path,
    handbook_path: Path,
) -> list[KnowledgeDocument]:
    """Load the real knowledge sources used by the Week 8 RAG system."""

    documents = [
        load_markdown_document(mapping_path),
        load_pdf_document(handbook_path),
    ]

    if not documents:
        raise RuntimeError(
            "No knowledge documents were loaded."
        )

    return documents


def prepare_knowledge_chunks(
    documents: list[KnowledgeDocument],
    chunk_size: int,
    overlap: int,
) -> list[KnowledgeChunk]:
    """Split all knowledge documents into aligned chunks."""

    chunks: list[KnowledgeChunk] = []

    for document in documents:
        document_chunks = chunk_text(
            text=document.content,
            source=document.source,
            section=None,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        if not document_chunks:
            print(
                f"Warning: no chunks generated for "
                f"{document.source}"
            )
            continue

        chunks.extend(document_chunks)

        print(
            f"Prepared {len(document_chunks)} chunks "
            f"from {document.source}"
        )

    if not chunks:
        raise RuntimeError(
            "No knowledge chunks were generated."
        )

    return chunks


def generate_embeddings(
    provider: BaseEmbeddingProvider,
    chunks: list[KnowledgeChunk],
    batch_size: int,
) -> np.ndarray:
    """Generate embeddings for knowledge chunks in batches."""

    if not chunks:
        raise ValueError(
            "No knowledge chunks were provided for embedding."
        )

    texts = [
        chunk.text
        for chunk in chunks
    ]

    all_embeddings: list[list[float]] = []

    total_batches = (
        len(texts) + batch_size - 1
    ) // batch_size

    for start in range(
        0,
        len(texts),
        batch_size,
    ):
        batch = texts[
            start : start + batch_size
        ]

        batch_number = (
            start // batch_size + 1
        )

        print(
            f"Embedding batch "
            f"{batch_number}/{total_batches} "
            f"({len(batch)} chunks)..."
        )

        batch_embeddings = (
            provider.embed_documents(batch)
        )

        if len(batch_embeddings) != len(batch):
            raise RuntimeError(
                "Embedding response count does not match "
                "input chunk count."
            )

        all_embeddings.extend(
            batch_embeddings
        )

    embeddings = np.asarray(
        all_embeddings,
        dtype=np.float32,
    )

    if embeddings.ndim != 2:
        raise RuntimeError(
            "Expected a 2D embedding matrix, "
            f"received shape {embeddings.shape}."
        )

    if embeddings.shape[0] != len(chunks):
        raise RuntimeError(
            "Embedding row count does not match "
            "knowledge chunk count."
        )

    if not np.isfinite(embeddings).all():
        raise RuntimeError(
            "Embedding matrix contains NaN or infinite values."
        )

    return embeddings


def build_metadata(
    chunks: list[KnowledgeChunk],
) -> list[dict[str, Any]]:
    """Create metadata aligned one-to-one with embedding rows."""

    metadata: list[dict[str, Any]] = []

    for chunk in chunks:
        metadata.append(
            {
                "chunk_id": chunk.chunk_id,
                "source": chunk.source,
                "section": chunk.section,
                "text": chunk.text,
            }
        )

    return metadata


def write_metadata_jsonl(
    output_path: Path,
    metadata: list[dict[str, Any]],
) -> None:
    """Write metadata with explicit embedding-row alignment."""

    temporary_path = output_path.with_suffix(
        f"{output_path.suffix}.tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        for row_index, record in enumerate(metadata):
            aligned_record = {
                "embedding_row": row_index,
                **record,
            }

            file.write(
                json.dumps(
                    aligned_record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    os.replace(
        temporary_path,
        output_path,
    )


def save_artifacts(
    output_dir: Path,
    embeddings: np.ndarray,
    metadata: list[dict[str, Any]],
    model: str,
    batch_size: int,
    chunk_size: int,
    overlap: int,
    source_documents: list[KnowledgeDocument],
) -> None:
    """Persist knowledge embeddings, metadata, FAISS index, and manifest."""

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    embeddings_path = (
        output_dir
        / "knowledge_embeddings.npy"
    )

    metadata_path = (
        output_dir
        / "knowledge_metadata.jsonl"
    )

    index_path = (
        output_dir
        / "knowledge.faiss"
    )

    manifest_path = (
        output_dir
        / "manifest.json"
    )

    temporary_embeddings_path = (
        output_dir
        / "knowledge_embeddings.tmp.npy"
    )

    np.save(
        temporary_embeddings_path,
        embeddings,
    )

    os.replace(
        temporary_embeddings_path,
        embeddings_path,
    )

    write_metadata_jsonl(
        output_path=metadata_path,
        metadata=metadata,
    )

    index = build_cosine_index(
        embeddings
    )

    save_index(
        index=index,
        output_path=index_path,
    )

    manifest = {
        "created_at_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "embedding_model": model,
        "document_count": len(
            source_documents
        ),
        "chunk_count": int(
            embeddings.shape[0]
        ),
        "embedding_dimension": int(
            embeddings.shape[1]
        ),
        "embedding_dtype": str(
            embeddings.dtype
        ),
        "batch_size": batch_size,
        "chunk_size": chunk_size,
        "overlap": overlap,
        "sources": [
            document.source
            for document in source_documents
        ],
        "embeddings_file": (
            embeddings_path.name
        ),
        "metadata_file": (
            metadata_path.name
        ),
        "faiss_index_file": (
            index_path.name
        ),
        "metadata_alignment": (
            "metadata embedding_row equals the "
            "corresponding row in "
            "knowledge_embeddings.npy and FAISS index"
        ),
    }

    temporary_manifest_path = (
        manifest_path.with_suffix(
            ".json.tmp"
        )
    )

    with temporary_manifest_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            manifest,
            file,
            indent=2,
        )

    os.replace(
        temporary_manifest_path,
        manifest_path,
    )

    print(
        "\nKnowledge index artifacts "
        "created successfully:"
    )
    print(
        f"  Embeddings: {embeddings_path}"
    )
    print(
        f"  Metadata:   {metadata_path}"
    )
    print(
        f"  FAISS:      {index_path}"
    )
    print(
        f"  Manifest:   {manifest_path}"
    )
    print(
        f"  Shape:      {embeddings.shape}"
    )
    print(
        f"  Documents:  {len(source_documents)}"
    )
    print(
        f"  Chunks:     {len(metadata)}"
    )


def main() -> None:
    args = parse_args()

    print("Loading knowledge documents...")

    documents = load_knowledge_documents(
        mapping_path=args.mapping_path,
        handbook_path=args.handbook_path,
    )

    print(
        f"Loaded knowledge documents: "
        f"{len(documents)}"
    )

    chunks = prepare_knowledge_chunks(
        documents=documents,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )

    print(
        f"Total knowledge chunks: "
        f"{len(chunks)}"
    )

    print(
        "\nSample chunk:"
    )
    print("-" * 80)
    print(
        f"Source: {chunks[0].source}"
    )
    print(
        f"Chunk ID: {chunks[0].chunk_id}"
    )
    print(chunks[0].text)
    print("-" * 80)

    provider = get_embedding_provider(
        model=args.model,
    )

    embeddings = generate_embeddings(
        provider=provider,
        chunks=chunks,
        batch_size=args.batch_size,
    )

    metadata = build_metadata(
        chunks
    )

    save_artifacts(
        output_dir=args.output_dir,
        embeddings=embeddings,
        metadata=metadata,
        model=args.model,
        batch_size=args.batch_size,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        source_documents=documents,
    )


if __name__ == "__main__":
    main()