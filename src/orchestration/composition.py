from __future__ import annotations

import re
from pathlib import Path

from src.agents.comparable_value_agent import (
    ComparableValueAgent,
)
from src.agents.intent_agent import IntentAgent
from src.agents.market_agent import MarketAgent
from src.agents.search_agent import SearchAgent
from src.orchestration.adapters import (
    KnowledgeAdapter,
    MarketAdapter,
    PropertySearchAdapter,
    RecommendationAdapter,
)
from src.orchestration.orchestrator import (
    Orchestrator,
)
from src.orchestration.router import (
    IntentRouter,
)
from src.providers.factory import (
    get_embedding_provider,
    get_llm_provider,
)
from src.knowledge.grounded_answerer import (
    GroundedKnowledgeAnswerer,
)
from src.recommendation.hybrid_recommendation import (
    HybridRecommendationService,
)
from src.recommendation.hybrid_similarity import (
    SimilarListingRetriever,
)
from src.search.knowledge_retriever import (
    KnowledgeRetriever,
)
from src.search.mysql_search_repository import (
    MySQLSearchRepository,
)
from src.search.mysql_sold_comp_repository import (
    MySQLSoldCompRepository,
)
from src.workflow.graph import (
    PropertySearchGraph,
)


DEFAULT_LISTING_EMBEDDINGS_PATH = Path(
    "artifacts/embeddings/full/"
    "listing_embeddings.npy"
)

DEFAULT_LISTING_METADATA_PATH = Path(
    "artifacts/embeddings/full/"
    "listing_metadata.jsonl"
)

DEFAULT_KNOWLEDGE_INDEX_PATH = Path(
    "artifacts/knowledge/"
    "knowledge.faiss"
)

DEFAULT_KNOWLEDGE_METADATA_PATH = Path(
    "artifacts/knowledge/"
    "knowledge_metadata.jsonl"
)

# =====================================================================
# Recommendation target resolver
# =====================================================================


_EXPLICIT_LISTING_ID_PATTERN = re.compile(
    r"\blisting(?:\s+id)?\s*[:#]?\s*"
    r"([A-Za-z0-9][A-Za-z0-9_-]*)\b",
    flags=re.IGNORECASE,
)


def resolve_explicit_listing_id(
    query: str,
) -> str | None:
    """
    Resolve an explicitly named listing ID from the user query.

    Week 9 MVP intentionally requires an explicit listing reference.

    Supported examples:
        "Show me homes similar to listing TEST-001"
        "Find similar homes to listing id TEST-001"
        "More like listing #TEST-001"

    Session-based references such as "more like this" are intentionally
    deferred to the later memory extension.
    """

    match = _EXPLICIT_LISTING_ID_PATTERN.search(
        query
    )

    if match is None:
        return None

    return match.group(1)


# =====================================================================
# Composition root
# =====================================================================

def create_orchestrator(
    *,
    knowledge_index_path: Path= (
        DEFAULT_KNOWLEDGE_INDEX_PATH
    ),
    knowledge_metadata_path: Path = (
        DEFAULT_KNOWLEDGE_METADATA_PATH
    ), 
    listing_embeddings_path: Path = (
        DEFAULT_LISTING_EMBEDDINGS_PATH
    ),
    listing_metadata_path: Path = (
        DEFAULT_LISTING_METADATA_PATH
    ),
) -> Orchestrator:
    """
    Build the real Week 9 orchestrator from existing Week 3-8
    capabilities.

    This function is the application composition root. It wires
    infrastructure and services together but contains no business logic.
    """

    # -----------------------------------------------------------------
    # Shared repositories
    # -----------------------------------------------------------------

    active_listing_repository = (
        MySQLSearchRepository()
    )

    sold_comp_repository = (
        MySQLSoldCompRepository()
    )

    # -----------------------------------------------------------------
    # Search capability
    #
    # Reuse the existing complete PropertySearchGraph rather than
    # rebuilding its internal agent pipeline here.
    # -----------------------------------------------------------------

    search_agent = SearchAgent(
        repository=active_listing_repository,
    )

    property_search_workflow = (
        PropertySearchGraph(
            search_agent=search_agent,
        )
    )

    search_adapter = PropertySearchAdapter(
        workflow=property_search_workflow,
    )

    # -----------------------------------------------------------------
    # Market capability
    #
    # Use a memory-free IntentAgent only to extract location criteria.
    # This prevents standalone market questions from mutating property
    # search session memory.
    # -----------------------------------------------------------------

    market_agent = MarketAgent(
        repository=sold_comp_repository,
    )

    market_intent_agent = IntentAgent(
        memory=None,
    )

    market_adapter = MarketAdapter(
        market_agent=market_agent,
        intent_agent=market_intent_agent,
    )

    # -----------------------------------------------------------------
    # Similar-home recommendation capability
    # -----------------------------------------------------------------

    similarity_retriever = (
        SimilarListingRetriever(
            embeddings_path=(
                listing_embeddings_path
            ),
            metadata_path=(
                listing_metadata_path
            ),
        )
    )

    recommendation_service = (
        HybridRecommendationService(
            similarity_retriever=(
                similarity_retriever
            ),
            market_agent=market_agent,
            comparable_value_agent=(
                ComparableValueAgent()
            ),
        )
    )

    recommendation_adapter = (
        RecommendationAdapter(
            service=(
                recommendation_service
            ),
            listing_id_resolver=(
                resolve_explicit_listing_id
            ),
        )
    )

    # -----------------------------------------------------------------
    # Week 8 grounded knowledge RAG
    # -----------------------------------------------------------------

    embedding_provider = (
        get_embedding_provider()
    )

    llm_provider = (
        get_llm_provider()
    )

    knowledge_retriever = (
        KnowledgeRetriever(
            provider=embedding_provider,
            index_path=knowledge_index_path,
            metadata_path=(
                knowledge_metadata_path
            ),
        )
    )

    knowledge_answerer = (
        GroundedKnowledgeAnswerer(
            retriever=knowledge_retriever,
            llm_provider=llm_provider,
            top_k=6,
        )
    )

    knowledge_adapter = KnowledgeAdapter(
        answer_callable=(
            knowledge_answerer.answer
        )
    )

    # -----------------------------------------------------------------
    # Top-level Week 9 router + orchestrator
    # -----------------------------------------------------------------

    router = IntentRouter()

    return Orchestrator(
        router=router.route,
        search_handler=search_adapter,
        market_handler=market_adapter,
        recommendation_handler=(
            recommendation_adapter
        ),
        knowledge_handler=(
            knowledge_adapter
        ),
    )