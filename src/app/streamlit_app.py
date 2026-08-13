from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

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


# =====================================================================
# Header
# =====================================================================


st.title(
    "🏠 Real Estate Agentic Copilot"
)

st.caption(
    "Structured property search, full-corpus semantic retrieval, "
    "hybrid similar-home recommendation, sold-comparable analysis, "
    "and LangGraph-based property reasoning."
)


search_tab, similar_tab = st.tabs(
    [
        "🔎 Property Search",
        "🏡 Similar Home Recommendation",
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