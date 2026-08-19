from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.providers.base import BaseLLMProvider
from src.search.knowledge_retriever import KnowledgeRetriever


NO_EVIDENCE_ANSWER = "No sufficient evidence found."


@dataclass(frozen=True)
class RAGSource:
    source: str
    chunk_id: str
    score: float


@dataclass(frozen=True)
class RAGResponse:
    answer: str
    sources: list[RAGSource]


class RAGService:
    """Grounded question answering over retrieved knowledge chunks."""

    def __init__(
        self,
        retriever: KnowledgeRetriever,
        llm_provider: BaseLLMProvider,
        top_k: int = 4,
    ) -> None:
        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        self.retriever = retriever
        self.llm_provider = llm_provider
        self.top_k = top_k

    def _build_context(
        self,
        results: list[dict[str, Any]],
    ) -> str:
        """Format retrieved chunks into grounded LLM context."""

        context_parts: list[str] = []

        for index, result in enumerate(
            results,
            start=1,
        ):
            context_parts.append(
                "\n".join(
                    [
                        f"[Source {index}]",
                        f"Document: {result['source']}",
                        f"Chunk ID: {result['chunk_id']}",
                        f"Retrieval score: {result['score']:.4f}",
                        "Content:",
                        result["text"],
                    ]
                )
            )

        return "\n\n".join(
            context_parts
        )

    def _build_system_prompt(self) -> str:
        return (
            "You are a grounded real-estate knowledge assistant. "
            "Answer the user's question using only the retrieved "
            "source context provided to you. "
            "Do not use outside knowledge, assumptions, or prior "
            "knowledge to fill missing information. "
            "A source merely mentioning a term or repeating the "
            "question does not count as sufficient evidence. "
            "Only provide an answer when the retrieved context "
            "directly supports it. "
            f"If the context is insufficient, respond exactly with: "
            f"{NO_EVIDENCE_ANSWER}"
        )

    def _build_user_prompt(
        self,
        question: str,
        context: str,
    ) -> str:
        return (
            "Retrieved context:\n\n"
            f"{context}\n\n"
            "Question:\n"
            f"{question}\n\n"
            "Answer the question concisely and only from "
            "the retrieved context."
        )

    def answer(
        self,
        question: str,
    ) -> RAGResponse:
        """Retrieve evidence and generate a grounded answer."""

        if not question or not question.strip():
            raise ValueError(
                "Question must not be empty."
            )

        results = self.retriever.search(
            query=question.strip(),
            top_k=self.top_k,
        )

        if not results:
            return RAGResponse(
                answer=NO_EVIDENCE_ANSWER,
                sources=[],
            )

        context = self._build_context(
            results
        )

        answer = self.llm_provider.generate(
            system_prompt=self._build_system_prompt(),
            user_prompt=self._build_user_prompt(
                question=question.strip(),
                context=context,
            ),
        ).strip()

        sources = [
            RAGSource(
                source=result["source"],
                chunk_id=result["chunk_id"],
                score=float(
                    result["score"]
                ),
            )
            for result in results
        ]

        return RAGResponse(
            answer=answer,
            sources=sources,
        )