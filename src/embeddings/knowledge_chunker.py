from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    source: str
    section: str | None
    text: str


def chunk_text(
    text: str,
    source: str,
    section: str | None = None,
    chunk_size: int = 600,
    overlap: int = 100,
) -> list[KnowledgeChunk]:
    """Split document text into overlapping knowledge chunks."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be >= 0 and smaller than chunk_size."
        )

    normalized_text = text.strip()

    if not normalized_text:
        return []

    chunks: list[KnowledgeChunk] = []

    start = 0
    chunk_number = 0

    while start < len(normalized_text):
        end = min(
            start + chunk_size,
            len(normalized_text),
        )

        chunk_content = normalized_text[start:end].strip()

        if chunk_content:
            chunks.append(
                KnowledgeChunk(
                    chunk_id=f"{source}::chunk_{chunk_number}",
                    source=source,
                    section=section,
                    text=chunk_content,
                )
            )

            chunk_number += 1

        if end >= len(normalized_text):
            break

        start += chunk_size - overlap

    return chunks