from src.config.settings import settings
from src.providers.base import BaseLLMProvider
from src.providers.embedding_base import BaseEmbeddingProvider
from src.providers.openai_embedding_provider import (
    OpenAIEmbeddingProvider,
)
from src.providers.openai_provider import OpenAIProvider


def get_llm_provider() -> BaseLLMProvider:
    if settings.llm_provider == "openai":
        return OpenAIProvider()

    raise ValueError(
        f"Unsupported LLM provider: {settings.llm_provider}"
    )


def get_embedding_provider(
    model: str | None = None,
) -> BaseEmbeddingProvider:
    if settings.embedding_provider == "openai":
        return OpenAIEmbeddingProvider(model=model)

    raise ValueError(
        "Unsupported embedding provider: "
        f"{settings.embedding_provider}"
    )