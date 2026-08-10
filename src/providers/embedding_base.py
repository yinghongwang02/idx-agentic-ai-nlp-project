from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """Interface for text embedding providers."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Generate an embedding for a single search query."""
        raise NotImplementedError

    @abstractmethod
    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate embeddings for a batch of documents."""
        raise NotImplementedError