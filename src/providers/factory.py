from src.config.settings import settings
from src.providers.base import BaseLLMProvider
from src.providers.openai_provider import OpenAIProvider


def get_llm_provider() -> BaseLLMProvider:
    if settings.llm_provider == "openai":
        return OpenAIProvider()

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")