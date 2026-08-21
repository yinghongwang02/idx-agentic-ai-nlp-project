from __future__ import annotations

from typing import Any

from src.providers.base import BaseLLMProvider
from src.search.knowledge_retriever import KnowledgeRetriever


class GroundedKnowledgeAnswerer:
    """Generate answers grounded in retrieved knowledge chunks."""

    def __init__(
        self,
        retriever: KnowledgeRetriever,
        llm_provider: BaseLLMProvider,
        top_k: int = 6,
        min_retrieval_score: float | None = None,
    ) -> None:
        self.retriever = retriever
        self.llm_provider = llm_provider
        self.top_k = top_k
        self.min_retrieval_score = min_retrieval_score

    def answer(
        self,
        question: str,
    ) -> dict[str, Any]:
        """Retrieve context and generate a grounded answer."""

        results = self.retriever.search(
            query=question,
            top_k=self.top_k,
        )

        if not results:
            return self._fallback_response(
                question=question,
                results=[],
            )

        max_score = float(
            results[0].get(
                "score",
                0.0,
            )
        )

        if (
            self.min_retrieval_score is not None
            and max_score < self.min_retrieval_score
        ):
            return self._fallback_response(
                question=question,
                results=results,
            )

        context = self._build_context(
            results
        )

        system_prompt = (
            "You are a real-estate knowledge assistant. "
            "Answer the user's question using only the provided context. "
            "Do not use outside knowledge. "
            "Do not invent unsupported facts. "
            "If the context does not contain enough information to answer "
            "the question, respond exactly with: "
            "\"I don't have enough information in the available "
            "knowledge sources.\" "
            "Keep the answer concise and direct."
        )

        user_prompt = (
            f"Context:\n{context}\n\n"
            f"Question:\n{question}"
        )

        answer_text = self.llm_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        ).strip()

        return {
            "question": question,
            "answer": answer_text,
            "sources": self._extract_sources(
                results
            ),
            "retrieval_results": results,
            "max_retrieval_score": max_score,
        }

    def _build_context(
        self,
        results: list[dict[str, Any]],
    ) -> str:
        """Format retrieved chunks into LLM context."""

        blocks: list[str] = []

        for rank, result in enumerate(
            results,
            start=1,
        ):
            source = str(
                result.get(
                    "source",
                    "unknown",
                )
            )

            section = result.get(
                "section"
            )

            text = str(
                result.get(
                    "text",
                    "",
                )
            )

            header = (
                f"[Source {rank}] "
                f"{source}"
            )

            if section:
                header += (
                    f" | Section: {section}"
                )

            blocks.append(
                f"{header}\n{text}"
            )

        return "\n\n".join(
            blocks
        )

    def _extract_sources(
        self,
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return unique source/section pairs."""

        seen: set[
            tuple[str, str | None]
        ] = set()

        sources: list[
            dict[str, Any]
        ] = []

        for result in results:
            source = str(
                result.get(
                    "source",
                    "unknown",
                )
            )

            section = result.get(
                "section"
            )

            key = (
                source,
                section,
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            sources.append(
                {
                    "source": source,
                    "section": section,
                }
            )

        return sources

    def _fallback_response(
        self,
        question: str,
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Return a fallback when evidence is insufficient."""

        max_score = (
            float(
                results[0].get(
                    "score",
                    0.0,
                )
            )
            if results
            else None
        )

        return {
            "question": question,
            "answer": (
                "I don't have enough information "
                "in the available knowledge sources."
            ),
            "sources": [],
            "retrieval_results": results,
            "max_retrieval_score": max_score,
        }