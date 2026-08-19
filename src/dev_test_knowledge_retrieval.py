from pathlib import Path

from src.providers.factory import (
    get_embedding_provider,
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


TEST_QUERIES = [
    "What does DOM mean?",
    "What columns are in california_sold?",
    "What is a list-to-close ratio?",
]


def main() -> None:
    provider = get_embedding_provider()

    retriever = KnowledgeRetriever(
        provider=provider,
        index_path=INDEX_PATH,
        metadata_path=METADATA_PATH,
    )

    for query in TEST_QUERIES:
        print("\n" + "=" * 100)
        print(f"QUERY: {query}")
        print("=" * 100)

        results = retriever.search(
            query=query,
            top_k=4,
        )

        for rank, result in enumerate(
            results,
            start=1,
        ):
            print(
                f"\nRank {rank}"
            )
            print(
                f"Score:  "
                f"{result['score']:.4f}"
            )
            print(
                f"Source: "
                f"{result['source']}"
            )
            print(
                f"Chunk:  "
                f"{result['chunk_id']}"
            )
            print(
                f"Row:    "
                f"{result['embedding_row']}"
            )
            print("Text:")
            print(
                result["text"]
            )


if __name__ == "__main__":
    main()