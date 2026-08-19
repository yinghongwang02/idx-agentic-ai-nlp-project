from pathlib import Path

from src.knowledge.rag_service import (
    RAGService,
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


TEST_QUESTIONS = [
    "What does DOM mean?",
    "What columns are in california_sold?",
    "What is a list-to-close ratio?",
]


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

    rag = RAGService(
        retriever=retriever,
        llm_provider=llm_provider,
        top_k=4,
    )

    for question in TEST_QUESTIONS:
        print(
            "\n"
            + "=" * 100
        )

        print(
            f"QUESTION: {question}"
        )

        print(
            "=" * 100
        )

        response = rag.answer(
            question
        )

        print(
            "\nANSWER:"
        )

        print(
            response.answer
        )

        print(
            "\nSOURCES:"
        )

        for source in response.sources:
            print(
                f"- {source.source} | "
                f"{source.chunk_id} | "
                f"score={source.score:.4f}"
            )


if __name__ == "__main__":
    main()