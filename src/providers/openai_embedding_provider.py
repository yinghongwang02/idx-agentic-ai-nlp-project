from openai import OpenAI

from src.config.settings import settings
from src.providers.embedding_base import BaseEmbeddingProvider


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI implementation of the embedding provider interface."""

    def __init__(
        self,
        model: str | None = None,
    ) -> None:
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required for OpenAI embeddings."
            )

        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = model or settings.openai_embedding_model

    def embed_query(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Query text must not be empty.")

        response = self.client.embeddings.create(
            model=self.model,
            input=text,
            encoding_format="float",
        )

        if len(response.data) != 1:
            raise RuntimeError(
                "Expected exactly one embedding for query text."
            )

        return response.data[0].embedding

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            raise ValueError("Document texts must not be empty.")

        if any(not text or not text.strip() for text in texts):
            raise ValueError(
                "Document texts must not contain empty strings."
            )

        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
            encoding_format="float",
        )

        ordered_data = sorted(
            response.data,
            key=lambda item: item.index,
        )

        embeddings = [
            item.embedding
            for item in ordered_data
        ]

        if len(embeddings) != len(texts):
            raise RuntimeError(
                "Embedding response count does not match input count."
            )

        return embeddings