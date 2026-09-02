from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import os

import numpy as np

import streamlit as st
from openai import OpenAI

from src.agents.comparable_value_agent import (
    ComparableValueAgent,
)
from src.agents.market_agent import MarketAgent
from src.agents.search_agent import SearchAgent
from src.recommendation.hybrid_recommendation import (
    HybridRecommendationService,
)
from src.recommendation.hybrid_similarity import (
    SimilarListingRetriever,
)
from src.search.mysql_search_repository import (
    MySQLSearchRepository,
)
from src.search.mysql_sold_comp_repository import (
    MySQLSoldCompRepository,
)
from src.workflow.graph import PropertySearchGraph

from src.orchestration.composition import (
    create_orchestrator,
)

from src.communication.email_draft_agent import (
    EmailDraftAgent,
)
from src.communication.email_approval import (
    EmailApprovalGate,
)
from src.communication.outbound_safety import (
    OutboundSafetyGuard,
)
from src.communication.mock_email_channel import (
    MockEmailChannel,
    SafeMockEmailSender,
)

DEFAULT_EMBEDDINGS_PATH = Path(
    "artifacts/embeddings/full/"
    "listing_embeddings.npy"
)

DEFAULT_METADATA_PATH = Path(
    "artifacts/embeddings/full/"
    "listing_metadata.jsonl"
)


# =====================================================================
# Resource construction
# =====================================================================


def create_workflow() -> PropertySearchGraph:
    """
    Create the existing LangGraph property-search workflow.

    Keep this workflow session-scoped because it owns mutable
    conversational search memory.
    """
    repository = MySQLSearchRepository()

    search_agent = SearchAgent(
        repository=repository,
    )

    return PropertySearchGraph(
        search_agent=search_agent,
    )


@st.cache_resource
def create_hybrid_recommendation_service(
) -> HybridRecommendationService:
    """
    Create the read-mostly hybrid recommendation infrastructure.

    The full embedding matrix is loaded once per Streamlit process
    instead of being reloaded on every UI rerun.
    """
    retriever = SimilarListingRetriever(
        embeddings_path=DEFAULT_EMBEDDINGS_PATH,
        metadata_path=DEFAULT_METADATA_PATH,
    )

    sold_comp_repository = (
        MySQLSoldCompRepository()
    )

    market_agent = MarketAgent(
        repository=sold_comp_repository,
    )

    comparable_value_agent = (
        ComparableValueAgent()
    )

    return HybridRecommendationService(
        similarity_retriever=retriever,
        market_agent=market_agent,
        comparable_value_agent=(
            comparable_value_agent
        ),
    )

@st.cache_resource
def create_unified_orchestrator():
    """
    Create the Week 9 unified LangGraph orchestrator once per
    Streamlit process.
    """

    return create_orchestrator()


# =====================================================================
# Week 8 knowledge-document RAG
# =====================================================================


KNOWLEDGE_EMBEDDINGS_CANDIDATES = [
    Path("artifacts/knowledge/knowledge_embeddings.npy"),
    Path("artifacts/knowledge/embeddings.npy"),
    Path("artifacts/knowledge_rag/knowledge_embeddings.npy"),
    Path("artifacts/knowledge_rag/embeddings.npy"),
]

KNOWLEDGE_METADATA_CANDIDATES = [
    Path("artifacts/knowledge/knowledge_metadata.jsonl"),
    Path("artifacts/knowledge/metadata.jsonl"),
    Path("artifacts/knowledge/chunks.jsonl"),
    Path("artifacts/knowledge_rag/knowledge_metadata.jsonl"),
    Path("artifacts/knowledge_rag/metadata.jsonl"),
    Path("artifacts/knowledge_rag/chunks.jsonl"),
]


def _find_knowledge_artifact(
    candidates: list[Path],
    suffix: str,
) -> Path:
    """Locate the Week 8 knowledge-index artifact without hard-coding one layout."""
    for path in candidates:
        if path.exists():
            return path

    artifacts_root = Path("artifacts")
    if artifacts_root.exists():
        matches = [
            path
            for path in artifacts_root.rglob(f"*{suffix}")
            if "knowledge" in str(path).lower()
        ]
        if matches:
            return sorted(matches)[0]

    raise FileNotFoundError(
        "Could not locate the Week 8 knowledge-index artifact. "
        "Expected a knowledge-related file under artifacts/."
    )


def _chunk_text(record: dict) -> str:
    for key in (
        "text",
        "content",
        "chunk_text",
        "page_content",
        "document",
    ):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _chunk_source(record: dict) -> str:
    for key in ("source", "source_file", "filename", "document_name"):
        value = record.get(key)
        if value:
            return str(value)
    return "Unknown source"


def _chunk_section(record: dict) -> str | None:
    for key in ("section", "heading", "title"):
        value = record.get(key)
        if value:
            return str(value)
    return None


def _chunk_id(record: dict, index: int) -> str:
    for key in ("chunk_id", "id", "chunk"):
        value = record.get(key)
        if value is not None:
            return str(value)
    return f"chunk_{index}"


class StreamlitKnowledgeRAG:
    """Thin UI adapter over the pre-built Week 8 knowledge index.

    The evaluation script remains the source of truth for retrieval metrics.
    This class only loads the already-built index, retrieves top-k chunks, and
    generates a grounded answer for the demo UI.
    """

    def __init__(
        self,
        embeddings_path: Path,
        metadata_path: Path,
    ) -> None:
        self.embeddings_path = embeddings_path
        self.metadata_path = metadata_path
        self.embeddings = np.load(embeddings_path).astype(np.float32)

        with metadata_path.open("r", encoding="utf-8") as handle:
            self.metadata = [
                json.loads(line)
                for line in handle
                if line.strip()
            ]

        if len(self.metadata) != len(self.embeddings):
            raise ValueError(
                "Knowledge embeddings and metadata have different row counts: "
                f"{len(self.embeddings)} vs {len(self.metadata)}."
            )

        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.normalized_embeddings = self.embeddings / norms

        self.embedding_model = os.getenv(
            "KNOWLEDGE_EMBEDDING_MODEL",
            "text-embedding-3-small",
        )
        self.chat_model = os.getenv(
            "KNOWLEDGE_CHAT_MODEL",
            "gpt-4o-mini",
        )
        self.client = OpenAI()

    def retrieve(
        self,
        question: str,
        top_k: int = 6,
    ) -> list[dict]:
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=question,
        )
        query_vector = np.asarray(
            response.data[0].embedding,
            dtype=np.float32,
        )

        if query_vector.shape[0] != self.normalized_embeddings.shape[1]:
            raise ValueError(
                "Query embedding dimension does not match the stored "
                "knowledge index. Check KNOWLEDGE_EMBEDDING_MODEL."
            )

        query_norm = np.linalg.norm(query_vector)
        if query_norm == 0:
            raise ValueError("Received a zero-length query embedding.")

        scores = self.normalized_embeddings @ (query_vector / query_norm)
        k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[::-1][:k]

        results = []
        for rank, index in enumerate(top_indices, start=1):
            record = self.metadata[int(index)]
            results.append(
                {
                    "rank": rank,
                    "score": float(scores[index]),
                    "source": _chunk_source(record),
                    "section": _chunk_section(record),
                    "chunk_id": _chunk_id(record, int(index)),
                    "text": _chunk_text(record),
                    "metadata": record,
                }
            )
        return results

    def answer(
        self,
        question: str,
        retrieved: list[dict],
    ) -> str:
        context_blocks = []
        for item in retrieved:
            label = f"[{item['rank']}] {item['source']}"
            if item["section"]:
                label += f" — {item['section']}"
            label += f" — {item['chunk_id']}"
            context_blocks.append(
                f"{label}\n{item['text']}"
            )

        context = "\n\n".join(context_blocks)

        instructions = (
            "You are a document-aware real-estate knowledge assistant. "
            "Answer only from the retrieved context below. Do not use outside "
            "knowledge to fill missing facts. If the context does not support "
            "the answer, say that the provided knowledge documents do not "
            "contain enough information. Keep the answer concise and cite "
            "supporting chunks inline as [1], [2], etc."
        )

        response = self.client.responses.create(
            model=self.chat_model,
            instructions=instructions,
            input=(
                f"Question:\n{question}\n\n"
                f"Retrieved context:\n{context}"
            ),
        )
        return response.output_text.strip()

    def ask(
        self,
        question: str,
        top_k: int = 6,
    ) -> tuple[str, list[dict]]:
        retrieved = self.retrieve(question, top_k=top_k)
        answer = self.answer(question, retrieved)
        return answer, retrieved


@st.cache_resource
def create_knowledge_rag_service() -> StreamlitKnowledgeRAG:
    embeddings_path = _find_knowledge_artifact(
        KNOWLEDGE_EMBEDDINGS_CANDIDATES,
        ".npy",
    )
    metadata_path = _find_knowledge_artifact(
        KNOWLEDGE_METADATA_CANDIDATES,
        ".jsonl",
    )
    return StreamlitKnowledgeRAG(
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
    )


# =====================================================================
# Streamlit configuration
# =====================================================================


st.set_page_config(
    page_title="Real Estate Agentic Copilot",
    page_icon="🏠",
    layout="wide",
)


# =====================================================================
# Session state
# =====================================================================


if "workflow" not in st.session_state:
    st.session_state.workflow = (
        create_workflow()
    )


if "search_history" not in st.session_state:
    st.session_state.search_history = []


if "hybrid_history" not in st.session_state:
    st.session_state.hybrid_history = []


if "knowledge_history" not in st.session_state:
    st.session_state.knowledge_history = []

if "unified_history" not in st.session_state:
    st.session_state.unified_history = []

if "unified_session_id" not in st.session_state:
    st.session_state.unified_session_id = (
        f"streamlit-{id(st.session_state)}"
    )


# ---------------------------------------------------------------------
# Week 11 email draft / approval / mock-delivery state
# ---------------------------------------------------------------------

if "latest_unified_result" not in st.session_state:
    st.session_state.latest_unified_result = None

if "latest_unified_query" not in st.session_state:
    st.session_state.latest_unified_query = ""

if "email_draft" not in st.session_state:
    st.session_state.email_draft = None

if "email_approval" not in st.session_state:
    st.session_state.email_approval = None

if "email_delivery" not in st.session_state:
    st.session_state.email_delivery = None

if "email_safety_result" not in st.session_state:
    st.session_state.email_safety_result = None

if "mock_email_channel" not in st.session_state:
    st.session_state.mock_email_channel = MockEmailChannel()

if "email_draft_agent" not in st.session_state:
    st.session_state.email_draft_agent = EmailDraftAgent()

if "email_approval_gate" not in st.session_state:
    st.session_state.email_approval_gate = EmailApprovalGate()

if "outbound_safety_guard" not in st.session_state:
    st.session_state.outbound_safety_guard = OutboundSafetyGuard()

if "safe_mock_email_sender" not in st.session_state:
    st.session_state.safe_mock_email_sender = SafeMockEmailSender(
        channel=st.session_state.mock_email_channel,
        safety_guard=st.session_state.outbound_safety_guard,
    )

# =====================================================================
# Sidebar
# =====================================================================


with st.sidebar:
    st.header("😊 Session Memory")

    memory_snapshot = (
        st.session_state.workflow
        .get_memory_snapshot()
    )

    if memory_snapshot:
        st.json(memory_snapshot)
    else:
        st.caption(
            "No active search preferences."
        )

    if st.button(
        "Start New Search",
        use_container_width=True,
    ):
        st.session_state.workflow.clear_session()
        st.session_state.search_history = []
        st.rerun()

    st.divider()

    st.header("🕒 Search History")

    history = (
        st.session_state.search_history
    )

    if not history:
        st.caption(
            "No searches yet."
        )

    else:
        for item in history:
            title = (
                f"{item['timestamp']} | "
                f"{item['query']}"
            )

            with st.expander(title):
                st.metric(
                    "Matching Listings",
                    item["result_count"],
                )

                if item["top_listing"]:
                    st.write(
                        f"**Top Listing:** "
                        f"{item['top_listing']}"
                    )

                if item["intent"]:
                    st.write(
                        "**Parsed Intent**"
                    )

                    st.json(
                        item["intent"],
                        expanded=False,
                    )

    st.divider()

    st.header(
        "🏡 Similar-Home History"
    )

    hybrid_history = (
        st.session_state.hybrid_history
    )

    if not hybrid_history:
        st.caption(
            "No similar-home requests yet."
        )

    else:
        for item in hybrid_history:
            title = (
                f"{item['timestamp']} | "
                f"{item['listing_id']}"
            )

            with st.expander(title):
                st.metric(
                    "Recommendations",
                    item["result_count"],
                )

                if item["top_listing"]:
                    st.write(
                        f"**Top Match:** "
                        f"{item['top_listing']}"
                    )


    st.divider()

    st.header("📖 Knowledge RAG History")

    knowledge_history = st.session_state.knowledge_history

    if not knowledge_history:
        st.caption("No knowledge questions yet.")
    else:
        for item in knowledge_history:
            title = f"{item['timestamp']} | {item['question']}"
            with st.expander(title):
                st.metric("Retrieved Chunks", item["result_count"])
                if item.get("top_source"):
                    st.write(f"**Top Source:** {item['top_source']}")

    st.divider()

    st.header("✨💬 Unified Copilot History")

    unified_history = (
        st.session_state.unified_history
    )

    if not unified_history:
        st.caption(
            "No unified requests yet."
        )

    else:
        for item in unified_history:
            title = (
                f"{item['timestamp']} | "
                f"{item['query']}"
            )

            with st.expander(title):
                st.write(
                    f"**Route:** "
                    f"{item['route']}"
                )

                agents = item.get(
                    "agents_invoked",
                    [],
                )

                if agents:
                    st.write(
                        "**Agents:** "
                        + ", ".join(agents)
                    )

# =====================================================================
# Header
# =====================================================================


st.title(
    "🏠 Real Estate Agentic Copilot"
)

st.caption(
    "Structured property search, full-corpus semantic retrieval, "
    "hybrid similar-home recommendation, sold-comparable analysis, "
    "document-aware RAG, and LangGraph-based property reasoning."
)


(
    search_tab,
    similar_tab,
    knowledge_tab,
    unified_tab,
    email_tab,
) = st.tabs(
    [
        "🔎 Property Search",
        "🏡 Similar Home Recommendation",
        "📖 Knowledge Assistant",
        "✨💬 Unified Copilot",
        "📧 Email Approval",
    ]
)


# =====================================================================
# TAB 1 — EXISTING LANGGRAPH SEARCH
# =====================================================================


with search_tab:
    st.subheader(
        "Find homes from your requirements"
    )

    st.caption(
        "Use natural language to search for properties. "
        "Multi-turn preferences are retained in session memory."
    )

    query = st.text_input(
        "Enter a property search query",
        placeholder=(
            "Try: Find townhouses in Irvine with a garage, "
            "preferably with a pool"
        ),
        key="property_search_query",
    )

    if st.button(
        "Search Properties",
        key="property_search_button",
    ):
        if not query.strip():
            st.warning(
                "Please enter a search query."
            )

        else:
            with st.spinner(
                "Analyzing properties and market data..."
            ):
                state = (
                    st.session_state.workflow
                    .run(query)
                )

            if state.get("error"):
                st.error(
                    state["final_response"]
                )

            elif state.get("blocked"):
                st.error(
                    state["final_response"]
                )

            else:
                intent = state.get(
                    "intent"
                )

                recommendations = state.get(
                    "recommendations",
                    [],
                )

                top_listing = None

                if recommendations:
                    first_listing = (
                        recommendations[0]
                        .listing
                    )

                    top_listing = (
                        first_listing.listing_id
                        or first_listing.listing_key
                        or first_listing.unparsed_address
                    )

                st.session_state.search_history.insert(
                    0,
                    {
                        "timestamp": (
                            datetime.now()
                            .strftime("%H:%M:%S")
                        ),
                        "query": query,
                        "intent": (
                            intent.model_dump()
                            if intent is not None
                            else None
                        ),
                        "result_count": len(
                            recommendations
                        ),
                        "top_listing": (
                            top_listing
                        ),
                    },
                )

                st.session_state.search_history = (
                    st.session_state
                    .search_history[:5]
                )

            # ---------------------------------------------------------
            # Compliance
            # ---------------------------------------------------------

            query_compliance = state.get(
                "query_compliance"
            )

            if query_compliance is not None:
                st.subheader(
                    "Compliance Status"
                )

                if (
                    query_compliance.risk_level
                    == "green"
                ):
                    st.success(
                        "Query passed compliance checks."
                    )

                elif (
                    query_compliance.risk_level
                    == "yellow"
                ):
                    st.warning(
                        query_compliance.safe_rewrite
                    )

                else:
                    st.error(
                        query_compliance.refusal_message
                    )

            # ---------------------------------------------------------
            # Parsed intent
            # ---------------------------------------------------------

            intent = state.get(
                "intent"
            )

            if intent is not None:
                with st.expander(
                    "View structured search intent"
                ):
                    st.json(
                        intent.model_dump()
                    )

            # ---------------------------------------------------------
            # Recommendations
            # ---------------------------------------------------------

            recommendations = state.get(
                "recommendations",
                [],
            )

            if not state.get(
                "blocked"
            ):
                st.subheader(
                    "Top Recommendations"
                )

                if not recommendations:
                    st.info(
                        "No matching listings found."
                    )

                else:
                    for (
                        rank,
                        recommendation,
                    ) in enumerate(
                        recommendations,
                        start=1,
                    ):
                        listing = (
                            recommendation.listing
                        )

                        with st.container(
                            border=True
                        ):
                            listing_name = (
                                listing.listing_id
                                or listing.listing_key
                                or listing.unparsed_address
                            )

                            st.markdown(
                                f"### #{rank} "
                                f"{listing_name}"
                            )

                            (
                                metric_col1,
                                metric_col2,
                            ) = st.columns(2)

                            with metric_col1:
                                st.metric(
                                    "Recommendation Score",
                                    (
                                        f"{recommendation.overall_score:.2f}"
                                        "/100"
                                    ),
                                )

                            with metric_col2:
                                st.metric(
                                    "Recommendation",
                                    recommendation
                                    .recommendation_label,
                                )

                            (
                                score_col1,
                                score_col2,
                                score_col3,
                            ) = st.columns(3)

                            with score_col1:
                                st.metric(
                                    "Preference Match",
                                    (
                                        f"{recommendation.preference_match_score:.2f}"
                                    ),
                                )

                            with score_col2:
                                st.metric(
                                    "Comparable Value",
                                    (
                                        f"{recommendation.comparable_value_score:.2f}"
                                    ),
                                )

                            with score_col3:
                                st.metric(
                                    "Negotiation",
                                    (
                                        f"{recommendation.negotiation_score:.2f}"
                                    ),
                                )

                            st.write(
                                f"**Address:** "
                                f"{listing.unparsed_address}"
                            )

                            st.write(
                                f"**City:** "
                                f"{listing.city}"
                            )

                            if (
                                listing.list_price
                                is not None
                            ):
                                st.write(
                                    f"**Price:** "
                                    f"${listing.list_price:,.0f}"
                                )

                            st.write(
                                f"**Beds/Baths:** "
                                f"{listing.bedrooms_total} bed / "
                                f"{listing.bathrooms_total_integer} bath"
                            )

                            if (
                                listing.living_area
                                is not None
                            ):
                                st.write(
                                    f"**Living Area:** "
                                    f"{listing.living_area:,.0f} sqft"
                                )

                            st.write(
                                f"**Days on Market:** "
                                f"{listing.days_on_market}"
                            )

                            if recommendation.reasons:
                                with st.expander(
                                    "Why this property ranked here"
                                ):
                                    for reason in (
                                        recommendation.reasons
                                    ):
                                        st.write(
                                            f"- {reason}"
                                        )

                            if listing.public_remarks:
                                with st.expander(
                                    "Listing remarks"
                                ):
                                    st.write(
                                        listing.public_remarks
                                    )

            final_response = state.get(
                "final_response"
            )

            if final_response:
                st.subheader(
                    "Generated Explanation"
                )

                st.write(
                    final_response
                )


# =====================================================================
# TAB 2 — HYBRID SIMILAR-LISTING RECOMMENDATION
# =====================================================================


with similar_tab:
    st.subheader(
        "Find homes similar to a listing you like"
    )

    st.caption(
        "Enter an MLS listing ID. The system combines "
        "structured property similarity with full-corpus "
        "embedding similarity, then validates each recommendation "
        "against recent sold comparables."
    )

    st.info(
        "Hybrid similarity = 60% structured property similarity "
        "+ 40% semantic listing similarity."
    )

    target_listing_id = st.text_input(
        "Target Listing ID",
        placeholder=(
            "Example: 1159993017"
        ),
        key="similar_listing_id",
    )

    top_k = st.slider(
        "Number of recommendations",
        min_value=1,
        max_value=10,
        value=5,
        key="similar_top_k",
    )

    if st.button(
        "Find Similar Homes",
        key="similar_home_button",
    ):
        if not target_listing_id.strip():
            st.warning(
                "Please enter a listing ID."
            )

        else:
            try:
                service = (
                    create_hybrid_recommendation_service()
                )

                with st.spinner(
                    "Finding similar listings and "
                    "validating sold comparables..."
                ):
                    results = service.recommend(
                        target_listing_id=(
                            target_listing_id.strip()
                        ),
                        top_k=top_k,
                    )

            except ValueError as exc:
                st.error(
                    str(exc)
                )
                results = []

            except Exception as exc:
                st.error(
                    "Hybrid recommendation could "
                    "not be completed."
                )

                with st.expander(
                    "Technical details"
                ):
                    st.code(
                        str(exc)
                    )

                results = []

            if results:
                top_match = (
                    results[0]["listing"]
                )

                top_match_id = (
                    top_match.listing_id
                    or top_match.listing_key
                )

                st.session_state.hybrid_history.insert(
                    0,
                    {
                        "timestamp": (
                            datetime.now()
                            .strftime("%H:%M:%S")
                        ),
                        "listing_id": (
                            target_listing_id.strip()
                        ),
                        "result_count": len(
                            results
                        ),
                        "top_listing": (
                            top_match_id
                        ),
                    },
                )

                st.session_state.hybrid_history = (
                    st.session_state
                    .hybrid_history[:5]
                )

                st.success(
                    f"Found {len(results)} "
                    f"similar active listings."
                )

                for rank, result in enumerate(
                    results,
                    start=1,
                ):
                    listing = result[
                        "listing"
                    ]

                    validation = result[
                        "comp_validation"
                    ]

                    with st.container(
                        border=True
                    ):
                        listing_name = (
                            listing.listing_id
                            or listing.listing_key
                            or listing.unparsed_address
                        )

                        st.markdown(
                            f"### #{rank} "
                            f"{listing_name}"
                        )

                        (
                            hybrid_col,
                            structured_col,
                            semantic_col,
                        ) = st.columns(3)

                        with hybrid_col:
                            st.metric(
                                "Hybrid Similarity",
                                (
                                    f"{result['hybrid_similarity_score']:.2f}"
                                    "/100"
                                ),
                            )

                        with structured_col:
                            st.metric(
                                "Property-Attribute Similarity",
                                (
                                    f"{result['structured_similarity_score']:.2f}"
                                    "/60"
                                ),
                            )

                        with semantic_col:
                            st.metric(
                                "Semantic",
                                (
                                    f"{result['semantic_similarity']:.3f}"
                                ),
                            )

                        st.write(
                            f"**Address:** "
                            f"{listing.unparsed_address}"
                        )

                        st.write(
                            f"**City:** "
                            f"{listing.city}"
                        )

                        if (
                            listing.list_price
                            is not None
                        ):
                            st.write(
                                f"**Price:** "
                                f"${listing.list_price:,.0f}"
                            )

                        st.write(
                            f"**Beds/Baths:** "
                            f"{listing.bedrooms_total} bed / "
                            f"{listing.bathrooms_total_integer} bath"
                        )

                        if (
                            listing.living_area
                            is not None
                        ):
                            st.write(
                                f"**Living Area:** "
                                f"{listing.living_area:,.0f} sqft"
                            )

                        # ---------------------------------------------
                        # Similarity explanation
                        # ---------------------------------------------

                        with st.expander(
                            "Similarity breakdown"
                        ):
                            st.write(
                                f"**Property-Attribute Similarity:** "
                                f"{result['structured_similarity_score']:.2f}/60"
                            )

                            st.write(
                                f"**Semantic cosine similarity:** "
                                f"{result['semantic_similarity']:.4f}"
                            )

                            st.write(
                                f"**Semantic contribution:** "
                                f"{result['semantic_similarity_score']:.2f}/40"
                            )

                            st.caption(
                                "Property type is used as a "
                                "candidate compatibility guardrail "
                                "rather than another weighted score."
                            )

                        # ---------------------------------------------
                        # Sold-comp validation
                        # ---------------------------------------------

                        st.markdown(
                            "#### Sold-Comp Validation"
                        )

                        if (
                            validation["status"]
                            == "validated"
                        ):
                            (
                                comp_col1,
                                comp_col2,
                                comp_col3,
                            ) = st.columns(3)

                            with comp_col1:
                                st.metric(
                                    "Comp Match",
                                    validation[
                                        "match_level"
                                    ],
                                )

                            with comp_col2:
                                st.metric(
                                    "Comparable Sales",
                                    validation[
                                        "comp_count"
                                    ],
                                )

                            with comp_col3:
                                st.metric(
                                    "Evidence Quality",
                                    (
                                        f"{validation['comparable_quality_score']:.1f}"
                                        "/100"
                                    ),
                                )

                            asking_ppsf = validation[
                                "asking_price_per_sqft"
                            ]

                            comparable_ppsf = validation[
                                "comparable_median_price_per_sqft"
                            ]

                            ratio = validation[
                                "price_per_sqft_ratio"
                            ]

                            median_close = validation[
                                "comparable_median_close_price"
                            ]

                            (
                                value_col1,
                                value_col2,
                                value_col3,
                            ) = st.columns(3)

                            with value_col1:
                                st.metric(
                                    "Asking PPSF",
                                    (
                                        f"${asking_ppsf:,.0f}"
                                        if asking_ppsf
                                        is not None
                                        else "N/A"
                                    ),
                                )

                            with value_col2:
                                st.metric(
                                    "Comp Median PPSF",
                                    (
                                        f"${comparable_ppsf:,.0f}"
                                        if comparable_ppsf
                                        is not None
                                        else "N/A"
                                    ),
                                )

                            with value_col3:
                                st.metric(
                                    "Comparable Value",
                                    (
                                        f"{validation['comparable_value_score']:.1f}"
                                        "/100"
                                    ),
                                )

                            if ratio is not None:
                                st.write(
                                    f"**Asking / Comp PPSF Ratio:** "
                                    f"{ratio:.3f}"
                                )

                            if median_close is not None:
                                st.write(
                                    f"**Comparable Median Close Price:** "
                                    f"${median_close:,.0f}"
                                )

                            if validation["signals"]:
                                with st.expander(
                                    "Comp evidence"
                                ):
                                    for signal in (
                                        validation[
                                            "signals"
                                        ]
                                    ):
                                        st.write(
                                            f"- {signal}"
                                        )

                        else:
                            st.warning(
                                "Sold-comparable validation "
                                "was unavailable for this listing."
                            )

                        if listing.public_remarks:
                            with st.expander(
                                "Listing remarks"
                            ):
                                st.write(
                                    listing.public_remarks
                                )


# =====================================================================
# TAB 3 — WEEK 8 DOCUMENT-AWARE KNOWLEDGE RAG
# =====================================================================


with knowledge_tab:
    st.subheader("Ask the project knowledge base")

    st.caption(
        "Ask real-estate concept, MLS-field, terminology, or handbook "
        "questions. The assistant retrieves the most relevant document "
        "chunks and generates an answer grounded only in those sources."
    )

    st.info(
        "Week 8 pipeline: document chunks → embedding index → top-k "
        "retrieval → grounded generation. Retrieval evaluation remains "
        "separate in knowledge_retrieval_cases.json."
    )

    example_col1, example_col2, example_col3 = st.columns(3)
    with example_col1:
        st.caption("Example: What does DOM mean in real estate?")
    with example_col2:
        st.caption(
            "Example: Which field stores days on market in california_sold?"
        )
    with example_col3:
        st.caption("Example: What does the handbook say about RAG?")

    knowledge_question = st.text_input(
        "Ask a knowledge question",
        placeholder=(
            "Try: Which field stores days on market in california_sold?"
        ),
        key="knowledge_question",
    )

    knowledge_top_k = st.slider(
        "Retrieved chunks",
        min_value=1,
        max_value=8,
        value=6,
        key="knowledge_top_k",
    )

    if st.button(
        "Ask Knowledge Assistant",
        key="knowledge_ask_button",
    ):
        if not knowledge_question.strip():
            st.warning("Please enter a knowledge question.")
        else:
            try:
                service = create_knowledge_rag_service()

                with st.spinner(
                    "🎨🖊️ Generating a grounded answer from retrieved evidence..."
                ):
                    answer, retrieved = service.ask(
                        knowledge_question.strip(),
                        top_k=knowledge_top_k,
                    )

                st.session_state.knowledge_history.insert(
                    0,
                    {
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "question": knowledge_question.strip(),
                        "result_count": len(retrieved),
                        "top_source": (
                            retrieved[0]["source"] if retrieved else None
                        ),
                    },
                )
                st.session_state.knowledge_history = (
                    st.session_state.knowledge_history[:5]
                )

                st.markdown("### Grounded Answer")
                st.write(answer)

                st.markdown("### Retrieved Evidence")

                for item in retrieved:
                    section_text = (
                        f" — {item['section']}"
                        if item["section"]
                        else ""
                    )
                    expander_title = (
                        f"#{item['rank']} | {item['source']}"
                        f"{section_text} | score={item['score']:.4f}"
                    )

                    with st.expander(
                        expander_title,
                        expanded=(item["rank"] == 1),
                    ):
                        st.write(f"**Chunk:** {item['chunk_id']}")
                        st.write(f"**Similarity:** {item['score']:.4f}")
                        st.write(item["text"] or "No chunk text available.")

            except FileNotFoundError as exc:
                st.error(str(exc))
                st.caption(
                    "Build the Week 8 knowledge index first, then rerun "
                    "Streamlit. The app searches knowledge-related artifacts "
                    "under artifacts/."
                )

            except Exception as exc:
                st.error("Knowledge RAG could not be completed.")
                with st.expander("Technical details"):
                    st.code(str(exc))


# =====================================================================
# TAB 4 — WEEK 9 UNIFIED AGENTIC COPILOT
# =====================================================================


with unified_tab:
    st.subheader(
        "✨💬 Unified Agentic Copilot"
    )

    st.caption(
        "Ask a real-estate question in natural language. "
        "The Week 9 orchestrator automatically routes the request "
        "to property search, market analysis, similar-home "
        "recommendation, knowledge RAG, or multiple capabilities."
    )

    st.info(
        "The unified router supports single-capability requests "
        "and mixed-intent fan-out/fan-in orchestration."
    )

    example_col1, example_col2, example_col3 = st.columns(3)

    with example_col1:
        st.caption(
            "Search: Find homes in Irvine under $1.5M."
        )

    with example_col2:
        st.caption(
            "Knowledge: What does DOM mean in real estate?"
        )

    with example_col3:
        st.caption(
            "Mixed: Find homes in Irvine and tell me "
            "about the local market."
        )

    unified_query = st.text_input(
        "Ask the Unified Copilot",
        placeholder=(
            "Try: Find homes in Irvine under $1.5M "
            "and tell me about the local market"
        ),
        key="unified_query",
    )

    if st.button(
        "✨💬 Ask Unified Copilot",
        key="unified_ask_button",
    ):
        if not unified_query.strip():
            st.warning(
                "Please enter a question."
            )

        else:
            try:
                orchestrator = (
                    create_unified_orchestrator()
                )

                with st.spinner(
                    "✨💬 Routing your request and "
                    "coordinating capabilities..."
                ):
                    result = orchestrator.invoke(
                        unified_query.strip(),
                        session_id=(
                            st.session_state
                            .unified_session_id
                        ),
                    )

                # Persist the latest real orchestrator result so the
                # Week 11 email tab can create a draft on a later rerun.
                st.session_state.latest_unified_result = result
                st.session_state.latest_unified_query = (
                    unified_query.strip()
                )

                # A new application result invalidates any older email
                # approval / delivery state.
                st.session_state.email_draft = None
                st.session_state.email_approval = None
                st.session_state.email_delivery = None
                st.session_state.email_safety_result = None

                route = result.get(
                    "route",
                    "unknown",
                )

                routes = result.get(
                    "routes",
                    [],
                )

                agents_invoked = result.get(
                    "agents_invoked",
                    [],
                )

                errors = result.get(
                    "errors",
                    [],
                )

                final_response = result.get(
                    "final_response",
                    "",
                )

                st.session_state.unified_history.insert(
                    0,
                    {
                        "timestamp": (
                            datetime.now()
                            .strftime("%H:%M:%S")
                        ),
                        "query": unified_query.strip(),
                        "route": route,
                        "agents_invoked": (
                            agents_invoked
                        ),
                    },
                )

                st.session_state.unified_history = (
                    st.session_state
                    .unified_history[:5]
                )

                # -----------------------------------------------------
                # Routing metadata
                # -----------------------------------------------------

                st.markdown(
                    "### Orchestration"
                )

                (
                    route_col,
                    agents_col,
                ) = st.columns(2)

                with route_col:
                    st.metric(
                        "Selected Route",
                        str(route),
                    )

                with agents_col:
                    st.metric(
                        "Agents Invoked",
                        len(agents_invoked),
                    )

                if routes:
                    st.write(
                        "**Dispatched capabilities:** "
                        + ", ".join(routes)
                    )

                if agents_invoked:
                    st.write(
                        "**Agents invoked:** "
                        + ", ".join(
                            agents_invoked
                        )
                    )

                route_reason = result.get(
                    "route_reason",
                    "",
                )

                if route_reason:
                    with st.expander(
                        "Why this route was selected"
                    ):
                        st.write(
                            route_reason
                        )

                # -----------------------------------------------------
                # Unified response
                # -----------------------------------------------------

                st.markdown(
                    "### ✨💬 Unified Response"
                )

                if final_response:
                    st.write(
                        final_response
                    )

                else:
                    st.info(
                        "The orchestrator returned "
                        "no response content."
                    )

                # -----------------------------------------------------
                # Partial failures
                # -----------------------------------------------------

                if errors:
                    st.warning(
                        "The request completed with "
                        "partial capability failures."
                    )

                    with st.expander(
                        "Partial failure details"
                    ):
                        for error in errors:
                            st.write(
                                f"- {error}"
                            )

            except Exception as exc:
                st.error(
                    "The Unified Copilot could not "
                    "complete this request."
                )

                with st.expander(
                    "Technical details"
                ):
                    st.code(
                        str(exc)
                    )

# =====================================================================
# TAB 5 — WEEK 11 EMAIL DRAFT + HUMAN APPROVAL + MOCK DELIVERY
# =====================================================================

with email_tab:
    st.subheader(
        "📧 Email Draft, Human Approval & Safe Mock Delivery"
    )

    st.caption(
        "Generate an email from the latest real Unified Copilot result, "
        "preview it, explicitly approve or reject it, then pass it through "
        "the outbound safety guard before mock delivery."
    )

    st.info(
        "Safety invariant: no outbound delivery is allowed without an "
        "explicit human approval record. Mock delivery never contacts "
        "a real email provider."
    )

    latest_result = (
        st.session_state.latest_unified_result
    )

    if latest_result is None:
        st.warning(
            "Run a Search, Market, or Mixed request in the "
            "Unified Copilot tab first."
        )

    else:
        latest_route = latest_result.get(
            "route",
            "unknown",
        )

        latest_query = (
            st.session_state.latest_unified_query
        )

        route_col, source_col = st.columns(2)

        with route_col:
            st.metric(
                "Latest Route",
                str(latest_route),
            )

        with source_col:
            st.metric(
                "Source",
                "Real LangGraph Orchestrator",
            )

        if latest_query:
            st.write(
                "**Source query:** "
                f"{latest_query}"
            )

        recipient = st.text_input(
            "Recipient email",
            value="buyer@example.com",
            key="email_recipient",
        )

        if st.button(
            "Generate Email Draft",
            key="generate_email_draft_button",
        ):
            try:
                email_agent = (
                    st.session_state.email_draft_agent
                )

                search_result = latest_result.get(
                    "search_result"
                )

                market_result = latest_result.get(
                    "market_result"
                )

                draft = None

                # Search and mixed routes take priority because a mixed
                # result can include both recommendations and market data.
                if isinstance(search_result, dict):
                    recommendations = search_result.get(
                        "recommendations",
                        [],
                    )

                    if recommendations:
                        draft = (
                            email_agent
                            .draft_property_digest(
                                to=recipient,
                                listings=recommendations,
                                market_summary=market_result,
                                buyer_preferences=latest_query,
                            )
                        )

                # Standalone market route.
                if (
                    draft is None
                    and market_result is not None
                ):
                    draft = (
                        email_agent
                        .draft_weekly_market_report(
                            to=recipient,
                            market_summary=market_result,
                        )
                    )

                if draft is None:
                    st.warning(
                        "The latest result does not currently contain "
                        "a supported email payload. Use a Search, Market, "
                        "or Mixed query with property recommendations."
                    )

                else:
                    st.session_state.email_draft = draft
                    st.session_state.email_approval = None
                    st.session_state.email_delivery = None
                    st.session_state.email_safety_result = None

                    st.success(
                        "Draft created and queued for human approval."
                    )

            except Exception as exc:
                st.error(
                    "Email draft could not be created."
                )

                with st.expander(
                    "Technical details"
                ):
                    st.code(str(exc))

        draft = st.session_state.email_draft

        if draft is not None:
            st.markdown(
                "### Email Preview"
            )

            status_col, type_col = st.columns(2)

            with status_col:
                st.metric(
                    "Draft Status",
                    draft.status,
                )

            with type_col:
                st.metric(
                    "Draft Type",
                    draft.metadata.get(
                        "draft_type",
                        "unknown",
                    ),
                )

            st.write(
                f"**To:** {draft.to}"
            )

            st.write(
                f"**Subject:** {draft.subject}"
            )

            st.text_area(
                "Body",
                value=draft.body,
                height=320,
                disabled=True,
                key="email_body_preview",
            )

            st.caption(
                "The draft cannot be delivered while it remains "
                "pending approval."
            )

            approve_col, reject_col = st.columns(2)

            with approve_col:
                if st.button(
                    "✅ Approve & Mock Send",
                    key="approve_mock_send_button",
                    use_container_width=True,
                ):
                    try:
                        approval = (
                            st.session_state
                            .email_approval_gate
                            .approve(
                                draft,
                                decided_by=(
                                    "streamlit-user"
                                ),
                            )
                        )

                        safety_result = (
                            st.session_state
                            .outbound_safety_guard
                            .check(
                                approval
                            )
                        )

                        st.session_state.email_approval = (
                            approval
                        )

                        st.session_state.email_safety_result = (
                            safety_result
                        )

                        if not safety_result.allowed:
                            st.session_state.email_delivery = None

                        else:
                            delivery = (
                                st.session_state
                                .safe_mock_email_sender
                                .send_approved(
                                    approval,
                                    session_id=(
                                        st.session_state
                                        .unified_session_id
                                    ),
                                )
                            )

                            st.session_state.email_delivery = (
                                delivery
                            )

                    except Exception as exc:
                        st.session_state.email_delivery = None

                        st.error(
                            "Outbound email was blocked."
                        )

                        with st.expander(
                            "Technical details"
                        ):
                            st.code(str(exc))

            with reject_col:
                if st.button(
                    "❌ Reject",
                    key="reject_email_button",
                    use_container_width=True,
                ):
                    rejection = (
                        st.session_state
                        .email_approval_gate
                        .reject(
                            draft,
                            decided_by=(
                                "streamlit-user"
                            ),
                            reason=(
                                "Rejected in Streamlit "
                                "human-approval UI."
                            ),
                        )
                    )

                    safety_result = (
                        st.session_state
                        .outbound_safety_guard
                        .check(
                            rejection
                        )
                    )

                    st.session_state.email_approval = (
                        rejection
                    )

                    st.session_state.email_safety_result = (
                        safety_result
                    )

                    # Rejected email is intentionally never sent.
                    st.session_state.email_delivery = None

            approval = (
                st.session_state.email_approval
            )

            safety_result = (
                st.session_state.email_safety_result
            )

            delivery = (
                st.session_state.email_delivery
            )

            if approval is not None:
                st.markdown(
                    "### Human Approval Decision"
                )

                if approval.is_approved:
                    st.success(
                        "Explicit human approval recorded."
                    )
                else:
                    st.error(
                        "Email rejected by human reviewer."
                    )

                st.write(
                    f"**Decision:** {approval.status}"
                )

                st.write(
                    f"**Decided by:** {approval.decided_by}"
                )

                st.write(
                    "**Decision time:** "
                    f"{approval.decided_at.isoformat()}"
                )

                if approval.reason:
                    st.write(
                        f"**Reason:** {approval.reason}"
                    )

            if safety_result is not None:
                st.markdown(
                    "### Outbound Safety Check"
                )

                if safety_result.allowed:
                    st.success(
                        "Safety guard passed. Outbound action allowed."
                    )
                else:
                    st.error(
                        "Safety guard blocked outbound delivery."
                    )

                    for reason in safety_result.reasons:
                        st.write(
                            f"- {reason}"
                        )

            if delivery is not None:
                st.markdown(
                    "### Mock Delivery"
                )

                if delivery.success:
                    st.success(
                        "Mock email sent successfully. "
                        "No real email provider was contacted."
                    )

                    delivery_col1, delivery_col2 = (
                        st.columns(2)
                    )

                    with delivery_col1:
                        st.metric(
                            "Channel",
                            delivery.channel,
                        )

                    with delivery_col2:
                        st.metric(
                            "Delivery Status",
                            "mock_sent",
                        )

                    st.write(
                        f"**Recipient:** "
                        f"{delivery.recipient}"
                    )

                    st.write(
                        f"**Mock Message ID:** "
                        f"{delivery.message_id}"
                    )

                    sent_count = len(
                        st.session_state
                        .mock_email_channel
                        .sent_messages
                    )

                    st.caption(
                        "Messages recorded by mock channel "
                        f"this session: {sent_count}"
                    )

            st.divider()

            if st.button(
                "Clear Email Workflow",
                key="clear_email_workflow_button",
            ):
                st.session_state.email_draft = None
                st.session_state.email_approval = None
                st.session_state.email_delivery = None
                st.session_state.email_safety_result = None
                st.rerun()

