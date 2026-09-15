from __future__ import annotations


from src.agents.intent_agent import IntentAgent
from src.agents.market_agent import MarketAgent
from src.agents.search_agent import SearchAgent

from src.orchestration.orchestrator import Orchestrator
from src.orchestration.router import IntentRouter
from src.public_demo.demo_search_repository import (
    DemoSearchRepository,
)
from src.public_demo.demo_sold_comp_repository import (
    DemoSoldCompRepository,
)

from src.workflow.graph import PropertySearchGraph

from pathlib import Path

from src.agents.comparable_value_agent import ComparableValueAgent
from src.orchestration.composition import resolve_explicit_listing_id
from src.recommendation.hybrid_recommendation import (
    HybridRecommendationService,
)
from src.recommendation.hybrid_similarity import (
    SimilarListingRetriever,
)

from src.knowledge.grounded_answerer import GroundedKnowledgeAnswerer
from src.providers.factory import (
    get_embedding_provider,
    get_llm_provider,
)
from src.search.knowledge_retriever import KnowledgeRetriever

from src.orchestration.adapters import (
    KnowledgeAdapter,
    MarketAdapter,
    PropertySearchAdapter,
    RecommendationAdapter,
)


PUBLIC_LISTING_EMBEDDINGS_PATH = Path(
    "artifacts/public_demo/listing_embeddings.npy"
)

PUBLIC_LISTING_METADATA_PATH = Path(
    "artifacts/public_demo/listing_metadata.jsonl"
)

PUBLIC_KNOWLEDGE_INDEX_PATH = Path(
    "artifacts/public_demo/knowledge/knowledge.faiss"
)

PUBLIC_KNOWLEDGE_METADATA_PATH = Path(
    "artifacts/public_demo/knowledge/knowledge_metadata.jsonl"
)



def create_public_orchestrator() -> Orchestrator:
    """
    Build the public portfolio-demo orchestrator.

    Production business logic and orchestration are reused while
    private IDX data infrastructure is replaced with deterministic
    synthetic repositories.
    """

    # Public-safe repositories
    active_listing_repository = DemoSearchRepository()
    sold_comp_repository = DemoSoldCompRepository()

    # Property search
    search_agent = SearchAgent(
        repository=active_listing_repository,
    )

    property_search_workflow = PropertySearchGraph(
        search_agent=search_agent,
    )

    search_adapter = PropertySearchAdapter(
        workflow=property_search_workflow,
    )

    # Market analysis
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

    # Similar-home recommendation
    similarity_retriever = SimilarListingRetriever(
        embeddings_path=PUBLIC_LISTING_EMBEDDINGS_PATH,
        metadata_path=PUBLIC_LISTING_METADATA_PATH,
    )

    recommendation_service = HybridRecommendationService(
        similarity_retriever=similarity_retriever,
        market_agent=market_agent,
        comparable_value_agent=ComparableValueAgent(),
    )

    recommendation_adapter = RecommendationAdapter(
        service=recommendation_service,
        listing_id_resolver=resolve_explicit_listing_id,
    )

    embedding_provider = get_embedding_provider()
    llm_provider = get_llm_provider()

    knowledge_retriever = KnowledgeRetriever(
        provider=embedding_provider,
        index_path=PUBLIC_KNOWLEDGE_INDEX_PATH,
        metadata_path=PUBLIC_KNOWLEDGE_METADATA_PATH,
    )

    knowledge_answerer = GroundedKnowledgeAnswerer(
        retriever=knowledge_retriever,
        llm_provider=llm_provider,
        top_k=6,
    )

    knowledge_adapter = KnowledgeAdapter(
        answer_callable=knowledge_answerer.answer,
    )

    # Top-level router + orchestrator
    router = IntentRouter()

    return Orchestrator(
        router=router.route,
        search_handler=search_adapter,
        market_handler=market_adapter,
        recommendation_handler=recommendation_adapter,
        knowledge_handler=knowledge_adapter,
    )
