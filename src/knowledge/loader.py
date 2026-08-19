from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class KnowledgeDocument:
    source: str
    content: str


def load_markdown_document(
    path: Path,
) -> KnowledgeDocument:
    """Load a Markdown knowledge document."""

    if not path.exists():
        raise FileNotFoundError(
            f"Knowledge document not found: {path}"
        )

    content = path.read_text(
        encoding="utf-8",
    ).strip()

    if not content:
        raise ValueError(
            f"Knowledge document is empty: {path}"
        )

    return KnowledgeDocument(
        source=path.name,
        content=content,
    )


def load_pdf_document(
    path: Path,
) -> KnowledgeDocument:
    """Load text from a PDF knowledge document."""

    if not path.exists():
        raise FileNotFoundError(
            f"Knowledge document not found: {path}"
        )

    reader = PdfReader(path)

    pages: list[str] = []

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            pages.append(
                page_text.strip()
            )

    content = "\n\n".join(pages).strip()

    if not content:
        raise ValueError(
            f"No extractable text found in PDF: {path}"
        )

    return KnowledgeDocument(
        source=path.name,
        content=content,
    )