from pathlib import Path

from src.knowledge.grounded_answerer import (
    GroundedKnowledgeAnswerer,
)
from src.providers.factory import (
    get_embedding_provider,
    get_llm_provider,
)
from src.search.knowledge_retriever import (
    KnowledgeRetriever,
)


INDEX_PATH = Path(
    "artifacts/knowledge/knowledge.faiss"
)

METADATA_PATH = Path(
    "artifacts/knowledge/knowledge_metadata.jsonl"
)

TOP_K = 6


def main() -> None:
    embedding_provider = (
        get_embedding_provider()
    )

    llm_provider = (
        get_llm_provider()
    )

    retriever = KnowledgeRetriever(
        provider=embedding_provider,
        index_path=INDEX_PATH,
        metadata_path=METADATA_PATH,
    )

    answerer = GroundedKnowledgeAnswerer(
        retriever=retriever,
        llm_provider=llm_provider,
        top_k=TOP_K,
    )

    questions = [
        (
            "What does DOM mean "
            "in real estate?"
        ),
        (
            "Which MLS field maps "
            "to bedroom count?"
        ),
        (
            "Which california_sold fields "
            "would you use to calculate "
            "a list-to-close price ratio?"
        ),
        (
            "Does California allow "
            "dual agency?"
        ),
        (
            "What is the current average "
            "mortgage rate in California?"
        ),
    ]

    for question in questions:
        print()
        print("=" * 100)
        print(
            f"QUESTION: {question}"
        )
        print("=" * 100)

        result = answerer.answer(
            question
        )

        print("\nANSWER:")
        print(
            result["answer"]
        )

        print("\nMAX RETRIEVAL SCORE:")
        max_score = result.get(
            "max_retrieval_score"
        )

        if max_score is not None:
            print(
                f"{max_score:.4f}"
            )
        else:
            print(
                "N/A"
            )

        print("\nSOURCES:")

        sources = result.get(
            "sources",
            []
        )

        if not sources:
            print(
                "- None"
            )
        else:
            for source in sources:
                source_name = source.get(
                    "source"
                )

                section = source.get(
                    "section"
                )

                print(
                    f"- {source_name}"
                    f" | "
                    f"{section}"
                )


if __name__ == "__main__":
    main()