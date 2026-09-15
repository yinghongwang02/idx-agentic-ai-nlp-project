from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.embeddings.faiss_index import (
    build_cosine_index,
    save_index,
)
from src.knowledge.loader import load_markdown_document
from src.providers.factory import get_embedding_provider


DEFAULT_INPUT_PATH = Path(
    "data/public_demo/knowledge/real_estate_knowledge.md"
)

DEFAULT_OUTPUT_DIR = Path(
    "artifacts/public_demo/knowledge"
)


def split_markdown_sections(
    content: str,
) -> list[tuple[str, str]]:
    """
    Split a public Markdown knowledge document into H2 sections.

    Each H2 section becomes one semantically meaningful RAG chunk.
    """
    sections: list[tuple[str, str]] = []

    current_section: str | None = None
    current_lines: list[str] = []

    for line in content.splitlines():
        if line.startswith("## "):
            if current_section is not None:
                text = "\n".join(
                    current_lines
                ).strip()

                if text:
                    sections.append(
                        (
                            current_section,
                            text,
                        )
                    )

            current_section = line[3:].strip()
            current_lines = []

        elif current_section is not None:
            current_lines.append(line)

    if current_section is not None:
        text = "\n".join(
            current_lines
        ).strip()

        if text:
            sections.append(
                (
                    current_section,
                    text,
                )
            )

    return sections


def write_metadata(
    path: Path,
    metadata: list[dict[str, object]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        for record in metadata:
            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )


def main() -> None:
    document = load_markdown_document(
        DEFAULT_INPUT_PATH
    )

    sections = split_markdown_sections(
        document.content
    )

    if not sections:
        raise RuntimeError(
            "No public knowledge sections were found."
        )

    texts: list[str] = []
    metadata: list[dict[str, object]] = []

    for row_index, (section, text) in enumerate(
        sections
    ):
        embedding_text = (
            f"{section}\n\n{text}"
        )

        texts.append(embedding_text)

        metadata.append(
            {
                "embedding_row": row_index,
                "chunk_id": (
                    f"{document.source}::"
                    f"section_{row_index}"
                ),
                "source": document.source,
                "section": section,
                "text": text,
            }
        )

    print(
        f"Prepared public knowledge chunks: {len(texts)}"
    )

    provider = get_embedding_provider()

    raw_embeddings = provider.embed_documents(
        texts
    )

    embeddings = np.asarray(
        raw_embeddings,
        dtype=np.float32,
    )

    if embeddings.ndim != 2:
        raise RuntimeError(
            "Expected a 2D knowledge embedding matrix."
        )

    if embeddings.shape[0] != len(metadata):
        raise RuntimeError(
            "Knowledge embedding count does not match metadata."
        )

    if not np.isfinite(embeddings).all():
        raise RuntimeError(
            "Knowledge embeddings contain invalid values."
        )

    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    embeddings_path = (
        output_dir
        / "knowledge_embeddings.npy"
    )

    index_path = (
        output_dir
        / "knowledge.faiss"
    )

    metadata_path = (
        output_dir
        / "knowledge_metadata.jsonl"
    )

    np.save(
        embeddings_path,
        embeddings,
    )

    index = build_cosine_index(
        embeddings
    )

    save_index(
        index=index,
        output_path=index_path,
    )

    write_metadata(
        metadata_path,
        metadata,
    )

    manifest = {
        "source": document.source,
        "chunk_count": len(metadata),
        "embedding_model": provider.model,
        "embedding_dimension": int(
            embeddings.shape[1]
        ),
        "index_type": "FAISS IndexFlatIP",
        "similarity": "cosine",
    }

    manifest_path = (
        output_dir / "manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "\nPublic knowledge artifacts created successfully:"
    )
    print(f"  FAISS:      {index_path}")
    print(f"  Embeddings: {embeddings_path}")
    print(f"  Metadata:   {metadata_path}")
    print(f"  Manifest:   {manifest_path}")
    print(f"  Shape:      {embeddings.shape}")


if __name__ == "__main__":
    main()