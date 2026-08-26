from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.agents.intent_agent import IntentAgent
from src.agents.market_agent import MarketAgent
from src.knowledge.grounded_answerer import (
    GroundedKnowledgeAnswerer,
)
from src.providers.factory import (
    get_embedding_provider,
    get_llm_provider,
)
from src.recommendation.hybrid_recommendation import (
    HybridRecommendationService,
)
from src.search.knowledge_retriever import (
    KnowledgeRetriever,
)
if TYPE_CHECKING:
    from src.workflow.graph import PropertySearchGraph


DEFAULT_KNOWLEDGE_INDEX_PATH = Path(
    "artifacts/knowledge/knowledge.faiss"
)

DEFAULT_KNOWLEDGE_METADATA_PATH = Path(
    "artifacts/knowledge/knowledge_metadata.jsonl"
)

DEFAULT_KNOWLEDGE_TOP_K = 6


class SearchCapability:
    """
    Thin adapter over the existing PropertySearchGraph.
    """

    def __init__(
        self,
        workflow: PropertySearchGraph,
    ) -> None:
        self.workflow = workflow

    def run(
        self,
        query: str,
    ) -> dict[str, Any]:
        if not query or not query.strip():
            raise ValueError(
                "Search query must not be empty."
            )

        return self.workflow.run(
            query.strip()
        )


class MarketCapability:
    """
    Query-level adapter over the standalone MarketAgent.run() path.

    This capability extracts only the location information needed for
    market analysis and does not invoke listing-level comparable logic.
    """

    def __init__(
        self,
        market_agent: MarketAgent,
        intent_agent: IntentAgent | None = None,
    ) -> None:
        self.market_agent = market_agent

        self.intent_agent = (
            intent_agent
            if intent_agent is not None
            else IntentAgent(
                memory=None
            )
        )

    def run(
        self,
        query: str,
    ) -> Any:
        if not query or not query.strip():
            raise ValueError(
                "Market query must not be empty."
            )

        intent = self.intent_agent.run(
            query.strip()
        )

        city = intent.city

        if not city:
            raise ValueError(
                "A supported city is required for market analysis."
            )

        return self.market_agent.run(
            city=city
        )


class RecommendCapability:
    """
    Query-level adapter over HybridRecommendationService.

    The existing recommendation service requires a target listing ID,
    so this adapter extracts the listing identifier from the user query.
    """

    LISTING_ID_PATTERNS = (
        r"\blisting\s+(?:id\s+)?([A-Za-z0-9_-]+)\b",
        r"\bmls\s+(?:id\s+|number\s+|#\s*)?([A-Za-z0-9_-]+)\b",
        r"\bproperty\s+(?:id\s+)?([A-Za-z0-9_-]+)\b",
    )

    def __init__(
        self,
        service: HybridRecommendationService,
        top_k: int = 5,
    ) -> None:
        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        self.service = service
        self.top_k = top_k

    def run(
        self,
        query: str,
    ) -> list[dict[str, Any]]:
        if not query or not query.strip():
            raise ValueError(
                "Recommendation query must not be empty."
            )

        target_listing_id = (
            self.extract_listing_id(
                query
            )
        )

        if not target_listing_id:
            raise ValueError(
                "A target listing ID is required for "
                "similar-home recommendation."
            )

        return self.service.recommend(
            target_listing_id=target_listing_id,
            top_k=self.top_k,
        )

    @classmethod
    def extract_listing_id(
        cls,
        query: str,
    ) -> str | None:
        normalized_query = (
            str(query or "").strip()
        )

        for pattern in cls.LISTING_ID_PATTERNS:
            match = re.search(
                pattern,
                normalized_query,
                flags=re.IGNORECASE,
            )

            if match:
                return match.group(1)

        return None


class KnowledgeCapability:
    """
    Thin adapter over the Week 8 grounded knowledge assistant.
    """

    def __init__(
        self,
        answerer: GroundedKnowledgeAnswerer,
    ) -> None:
        self.answerer = answerer

    def run(
        self,
        query: str,
    ) -> dict[str, Any]:
        if not query or not query.strip():
            raise ValueError(
                "Knowledge query must not be empty."
            )

        return self.answerer.answer(
            query.strip()
        )


def create_knowledge_capability(
    index_path: Path = DEFAULT_KNOWLEDGE_INDEX_PATH,
    metadata_path: Path = DEFAULT_KNOWLEDGE_METADATA_PATH,
    top_k: int = DEFAULT_KNOWLEDGE_TOP_K,
) -> KnowledgeCapability:
    """
    Construct the production Week 8 knowledge capability using the
    existing provider abstraction and persisted FAISS knowledge index.
    """

    embedding_provider = (
        get_embedding_provider()
    )

    llm_provider = (
        get_llm_provider()
    )

    retriever = KnowledgeRetriever(
        provider=embedding_provider,
        index_path=index_path,
        metadata_path=metadata_path,
    )

    answerer = GroundedKnowledgeAnswerer(
        retriever=retriever,
        llm_provider=llm_provider,
        top_k=top_k,
    )

    return KnowledgeCapability(
        answerer=answerer
    )