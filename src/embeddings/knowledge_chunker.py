from __future__ import annotations

from dataclasses import dataclass

import re

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


def chunk_markdown_by_sections(
    text: str,
    source: str,
    chunk_size: int = 600,
    overlap: int = 100,
) -> list[KnowledgeChunk]:
    """Split Markdown by headings, then chunk within each section."""

    normalized_text = text.strip()

    if not normalized_text:
        return []

    heading_pattern = re.compile(
        r"(?m)^(##+)\s+(.+?)\s*$"
    )

    matches = list(
        heading_pattern.finditer(
            normalized_text
        )
    )

    if not matches:
        return chunk_text(
            text=normalized_text,
            source=source,
            section=None,
            chunk_size=chunk_size,
            overlap=overlap,
        )

    chunks: list[KnowledgeChunk] = []

    # Preserve any document-level introduction before the first heading.
    intro = normalized_text[
        : matches[0].start()
    ].strip()

    if intro:
        chunks.extend(
            chunk_text(
                text=intro,
                source=source,
                section=None,
                chunk_size=chunk_size,
                overlap=overlap,
            )
        )

    for index, match in enumerate(
        matches
    ):
        section_title = (
            match.group(2).strip()
        )

        section_start = (
            match.start()
        )

        section_end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(normalized_text)
        )

        section_text = normalized_text[
            section_start:section_end
        ].strip()

        section_chunks = chunk_text(
            text=section_text,
            source=source,
            section=section_title,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        chunks.extend(
            section_chunks
        )

    # Reassign chunk IDs so they remain globally unique within the source.
    return [
        KnowledgeChunk(
            chunk_id=(
                f"{source}::chunk_{index}"
            ),
            source=chunk.source,
            section=chunk.section,
            text=chunk.text,
        )
        for index, chunk in enumerate(
            chunks
        )
    ]