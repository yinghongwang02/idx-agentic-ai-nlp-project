from __future__ import annotations

import uuid

import streamlit as st

from src.public_demo.public_composition import (
    create_public_orchestrator,
)


# =====================================================================
# Page configuration
# =====================================================================

st.set_page_config(
    page_title="Real Estate Agentic Copilot",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =====================================================================
# Application resources
# =====================================================================

@st.cache_resource
def get_public_orchestrator():
    """
    Build the public portfolio orchestrator once per Streamlit process.

    The public composition uses synthetic real-estate data and
    public-safe retrieval artifacts only.
    """
    return create_public_orchestrator()


def initialize_session_state() -> None:
    """Initialize lightweight state used by the public demo."""

    if "public_session_id" not in st.session_state:
        st.session_state.public_session_id = (
            f"public-{uuid.uuid4().hex[:12]}"
        )

    if "latest_public_result" not in st.session_state:
        st.session_state.latest_public_result = None

    if "latest_public_query" not in st.session_state:
        st.session_state.latest_public_query = None


initialize_session_state()

# =====================================================================
# Presentation helpers
# =====================================================================


def format_currency(value) -> str:
    """Format an optional numeric value as US currency."""
    if value is None:
        return "—"

    return f"${value:,.0f}"


def render_search_result(result: dict) -> None:
    """Render ranked property-search recommendations and score breakdowns."""

    errors = result.get("errors", [])

    if errors:
        st.error("The property search could not be fully completed.")

        with st.expander("Technical details"):
            for error in errors:
                st.write(f"- {error}")

        return

    search_result = result.get("search_result")

    if not isinstance(search_result, dict):
        final_response = result.get("final_response")
        if final_response:
            st.write(final_response)
        return

    recommendations = search_result.get("recommendations", [])

    st.caption(
        "Runtime debug — "
        f"search_result keys: {list(search_result.keys())}; "
        f"recommendations: {len(recommendations)}"
    )

    if not recommendations:
        st.warning("No properties matched the current search criteria.")
        return

    st.success(f"Found {len(recommendations)} ranked property recommendations.")
    st.caption(
        "Overall score combines preference match, comparable-value, "
        "and negotiation signals."
    )

    for rank, recommendation in enumerate(recommendations, start=1):
        listing = getattr(recommendation, "listing", None)

        if listing is None and isinstance(recommendation, dict):
            listing = recommendation.get("listing")

        if listing is None:
            continue

        def rec_value(name, default=None):
            if isinstance(recommendation, dict):
                return recommendation.get(name, default)
            return getattr(recommendation, name, default)

        address = getattr(listing, "unparsed_address", None) or "Demo property"
        city = getattr(listing, "city", None) or ""
        price = getattr(listing, "list_price", None)
        bedrooms = getattr(listing, "bedrooms_total", None)
        bathrooms = getattr(listing, "bathrooms_total_integer", None)
        living_area = getattr(listing, "living_area", None)
        property_type = getattr(listing, "property_sub_type", None)
        listing_id = (
            getattr(listing, "listing_id", None)
            or getattr(listing, "listing_key", None)
        )

        overall_score = rec_value("overall_score")
        preference_score = rec_value("preference_match_score")
        comparable_score = rec_value("comparable_value_score")
        negotiation_score = rec_value("negotiation_score")
        recommendation_label = rec_value("recommendation_label")
        reasons = rec_value("reasons", []) or []

        with st.container(border=True):
            title_col, price_col, score_col = st.columns([3, 1.2, 1.2])

            with title_col:
                st.markdown(f"#### {rank}. {address}")
                subtitle_parts = [part for part in (city, recommendation_label) if part]
                if subtitle_parts:
                    st.caption(" • ".join(subtitle_parts))

            with price_col:
                st.metric("List Price", format_currency(price))

            with score_col:
                st.metric(
                    "Overall Score",
                    f"{overall_score:.1f}/100"
                    if overall_score is not None
                    else "—",
                )

            if overall_score is not None:
                st.progress(
                    max(0.0, min(float(overall_score) / 100.0, 1.0))
                )

            detail_col1, detail_col2, detail_col3, detail_col4 = st.columns(4)

            detail_col1.metric(
                "Beds",
                bedrooms if bedrooms is not None else "—",
            )
            detail_col2.metric(
                "Baths",
                bathrooms if bathrooms is not None else "—",
            )
            detail_col3.metric(
                "Living Area",
                f"{living_area:,.0f} sq ft"
                if living_area is not None
                else "—",
            )
            detail_col4.metric(
                "Type",
                property_type or "—",
            )

            st.markdown("**Score Breakdown**")
            score_col1, score_col2, score_col3 = st.columns(3)

            score_col1.metric(
                "Preference Match",
                f"{preference_score:.1f}/100"
                if preference_score is not None
                else "—",
            )
            score_col2.metric(
                "Comparable Value",
                f"{comparable_score:.1f}/100"
                if comparable_score is not None
                else "—",
            )
            score_col3.metric(
                "Negotiation",
                f"{negotiation_score:.1f}/100"
                if negotiation_score is not None
                else "—",
            )

            if reasons:
                with st.expander("Why this property ranked here"):
                    for reason in reasons:
                        st.write(f"- {reason}")

            if listing_id:
                st.caption(f"Demo Listing ID: {listing_id}")


def render_market_result(result: dict) -> None:
    """Render structured market-analysis output."""

    errors = result.get("errors", [])

    if errors:
        st.error(
            "The market analysis could not be fully completed."
        )

        with st.expander("Technical details"):
            for error in errors:
                st.write(f"- {error}")

        return

    market = result.get("market_result")

    if market is None:
        final_response = result.get("final_response")

        if final_response:
            st.write(final_response)

        return

    city = getattr(
        market,
        "city",
        "Demo Market",
    )

    comp_count = getattr(
        market,
        "comp_count",
        None,
    )

    median_price = getattr(
        market,
        "median_close_price",
        None,
    )

    average_dom = getattr(
        market,
        "average_days_on_market",
        None,
    )

    sale_to_list = getattr(
        market,
        "average_sale_to_list_ratio",
        None,
    )

    ppsf = getattr(
        market,
        "average_price_per_sqft",
        None,
    )

    trend = getattr(
        market,
        "recent_trend",
        None,
    )

    st.markdown(
        f"### {city} Market Snapshot"
    )

    metric_col1, metric_col2, metric_col3, metric_col4 = (
        st.columns(4)
    )

    metric_col1.metric(
        "Median Close Price",
        format_currency(median_price),
    )

    metric_col2.metric(
        "Average DOM",
        (
            f"{average_dom:.1f} days"
            if average_dom is not None
            else "—"
        ),
    )

    metric_col3.metric(
        "Sale-to-List",
        (
            f"{sale_to_list:.1%}"
            if sale_to_list is not None
            else "—"
        ),
    )

    metric_col4.metric(
        "Average PPSF",
        (
            f"${ppsf:,.0f}"
            if ppsf is not None
            else "—"
        ),
    )

    if comp_count is not None:
        st.caption(
            f"Based on {comp_count} synthetic recent comparable sales."
        )

    if trend is not None:
        st.markdown("#### Recent Market Trend")

        direction = getattr(
            trend,
            "direction",
            None,
        )

        price_change = getattr(
            trend,
            "median_price_change_pct",
            None,
        )

        ppsf_change = getattr(
            trend,
            "median_ppsf_change_pct",
            None,
        )

        dom_change = getattr(
            trend,
            "average_dom_change",
            None,
        )

        sale_to_list_change = getattr(
            trend,
            "sale_to_list_change",
            None,
        )

        trend_col1, trend_col2, trend_col3, trend_col4 = (
            st.columns(4)
        )

        trend_col1.metric(
            "Direction",
            (
                str(direction).title()
                if direction
                else "—"
            ),
        )

        trend_col2.metric(
            "Median Price",
            (
                f"{price_change:+.1%}"
                if price_change is not None
                else "—"
            ),
            help="Recent period versus the previous period.",
        )

        trend_col3.metric(
            "PPSF",
            (
                f"{ppsf_change:+.1%}"
                if ppsf_change is not None
                else "—"
            ),
            help="Recent period versus the previous period.",
        )

        trend_col4.metric(
            "DOM",
            (
                f"{dom_change:+.1f} days"
                if dom_change is not None
                else "—"
            ),
            help="Change in average days on market.",
        )

        if sale_to_list_change is not None:
            st.caption(
                "Sale-to-list ratio change: "
                f"{sale_to_list_change:+.2%}"
            )

def render_recommendation_result(result: dict) -> None:
    """Render hybrid similar-home recommendations."""

    errors = result.get("errors", [])

    if errors:
        st.error(
            "The recommendation could not be fully completed."
        )

        with st.expander("Technical details"):
            for error in errors:
                st.write(f"- {error}")

        return

    recommendations = result.get(
        "recommendation_result"
    )

    if not recommendations:
        st.warning(
            "No similar-home recommendations were found."
        )
        return

    st.success(
        f"Found {len(recommendations)} similar homes."
    )

    for rank, recommendation in enumerate(
        recommendations,
        start=1,
    ):
        if not isinstance(recommendation, dict):
            continue

        listing = recommendation.get("listing")

        if listing is None:
            continue

        address = getattr(
            listing,
            "unparsed_address",
            None,
        ) or "Demo property"

        city = getattr(
            listing,
            "city",
            None,
        ) or ""

        price = getattr(
            listing,
            "list_price",
            None,
        )

        bedrooms = getattr(
            listing,
            "bedrooms_total",
            None,
        )

        bathrooms = getattr(
            listing,
            "bathrooms_total_integer",
            None,
        )

        living_area = getattr(
            listing,
            "living_area",
            None,
        )

        listing_id = (
            getattr(listing, "listing_id", None)
            or getattr(listing, "listing_key", None)
        )

        hybrid_score = recommendation.get(
            "hybrid_similarity_score"
        )

        structured_score = recommendation.get(
            "structured_similarity_score"
        )

        semantic_score = recommendation.get(
            "semantic_similarity_score"
        )

        with st.container(border=True):
            title_col, score_col = st.columns(
                [3, 1]
            )

            with title_col:
                st.markdown(
                    f"#### {rank}. {address}"
                )

                if city:
                    st.caption(city)

            with score_col:
                st.metric(
                    "Hybrid Similarity",
                    (
                        f"{hybrid_score:.1f}/100"
                        if hybrid_score is not None
                        else "—"
                    ),
                )

            detail_col1, detail_col2, detail_col3, detail_col4 = (
                st.columns(4)
            )

            detail_col1.metric(
                "Price",
                format_currency(price),
            )

            detail_col2.metric(
                "Beds",
                bedrooms if bedrooms is not None else "—",
            )

            detail_col3.metric(
                "Baths",
                bathrooms if bathrooms is not None else "—",
            )

            detail_col4.metric(
                "Living Area",
                (
                    f"{living_area:,.0f} sq ft"
                    if living_area is not None
                    else "—"
                ),
            )

            if (
                structured_score is not None
                or semantic_score is not None
            ):
                score_col1, score_col2 = st.columns(2)

                score_col1.metric(
                    "Structured Similarity",
                    (
                        f"{structured_score:.1f}"
                        if structured_score is not None
                        else "—"
                    ),
                )

                score_col2.metric(
                    "Semantic Similarity",
                    (
                        f"{semantic_score:.1f}"
                        if semantic_score is not None
                        else "—"
                    ),
                )

            if listing_id:
                st.caption(
                    f"Demo Listing ID: {listing_id}"
                )

def render_knowledge_result(result: dict) -> None:
    """Render a grounded public knowledge-RAG response."""

    errors = result.get("errors", [])

    if errors:
        st.error(
            "The knowledge assistant could not fully complete "
            "this request."
        )

        with st.expander("Technical details"):
            for error in errors:
                st.write(f"- {error}")

        return

    knowledge_result = result.get("knowledge_result")

    if knowledge_result is None:
        final_response = result.get("final_response")

        if final_response:
            st.write(final_response)

        return

    if isinstance(knowledge_result, dict):
        answer = knowledge_result.get(
            "answer",
            result.get("final_response", ""),
        )

        sources = knowledge_result.get(
            "sources",
            [],
        )

    else:
        answer = result.get(
            "final_response",
            str(knowledge_result),
        )

        sources = []

    st.markdown("#### Grounded Answer")

    st.write(answer)

    if sources:
        with st.expander(
            f"Retrieved Context ({len(sources)} chunks)"
        ):
            for index, source in enumerate(
                sources,
                start=1,
            ):
                if isinstance(source, dict):
                    source_name = source.get(
                        "source",
                        "Public knowledge guide",
                    )

                    section = source.get(
                        "section"
                    )

                    score = source.get(
                        "score"
                    )

                    text = source.get(
                        "text"
                    )

                else:
                    source_name = getattr(
                        source,
                        "source",
                        "Public knowledge guide",
                    )

                    section = getattr(
                        source,
                        "section",
                        None,
                    )

                    score = getattr(
                        source,
                        "score",
                        None,
                    )

                    text = getattr(
                        source,
                        "text",
                        None,
                    )

                title = (
                    section
                    or source_name
                    or f"Evidence {index}"
                )

                st.markdown(
                    f"**{index}. {title}**"
                )

                if score is not None:
                    st.caption(
                        f"Retrieval score: {score:.3f}"
                    )

                if text:
                    st.write(text)

def render_orchestration_summary(result: dict) -> None:
    """Render routing and agent-execution metadata."""

    route = result.get("route", "unknown")
    routes = result.get("routes", []) or []
    agents = result.get("agents_invoked", []) or []
    latency_ms = result.get("latency_ms")

    st.markdown("### Agent Orchestration")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Selected Route",
        str(route).upper(),
    )

    col2.metric(
        "Capabilities",
        len(routes) if routes else 1,
    )

    col3.metric(
        "Agents Invoked",
        len(agents),
    )

    col4.metric(
        "Latency",
        (
            f"{latency_ms:,.0f} ms"
            if latency_ms is not None
            else "—"
        ),
    )

    if routes:
        st.markdown(
            "**Dispatched capabilities:** "
            + " → ".join(
                str(item).title()
                for item in routes
            )
        )

    if agents:
        st.markdown(
            "**Executed agents:** "
            + " • ".join(
                str(agent).title()
                for agent in agents
            )
        )

    route_reason = result.get("route_reason")

    if route_reason:
        with st.expander("Why this route was selected"):
            st.write(route_reason)


def render_unified_result(result: dict) -> None:
    """Render a routed multi-capability result."""

    errors = result.get("errors", [])

    render_orchestration_summary(result)

    if errors:
        st.warning(
            "The orchestrator completed with one or more "
            "capability-level errors."
        )

        with st.expander("Technical details"):
            for error in errors:
                st.write(f"- {error}")

    route = result.get("route")
    routes = result.get("routes", []) or []

    active_routes = set(routes)

    if route and route != "mixed":
        active_routes.add(route)

    st.divider()

    if "search" in active_routes:
        st.markdown("## 🔎 Property Search Results")
        render_search_result(result)

    if "market" in active_routes:
        st.markdown("## 📈 Market Intelligence")
        render_market_result(result)

    if "recommend" in active_routes:
        st.markdown("## 🏡 Similar-Home Recommendations")
        render_recommendation_result(result)

    if "knowledge" in active_routes:
        st.markdown("## 📖 Knowledge Assistant")
        render_knowledge_result(result)

    final_response = result.get("final_response")

    if final_response:
        with st.expander("View Unified Text Response"):
            st.write(final_response)

# =====================================================================
# Sidebar
# =====================================================================

with st.sidebar:
    st.title("🏠 Agentic Copilot")

    st.caption(
        "Public portfolio demonstration of a multi-agent "
        "real-estate intelligence system."
    )

    st.divider()

    st.markdown("### System")

    st.markdown(
        """
        **Core capabilities**

        - Structured property search
        - Market intelligence
        - Hybrid home recommendation
        - Grounded knowledge RAG
        - Multi-agent orchestration
        """
    )

    st.divider()

    st.markdown("### Demo Environment")

    st.caption(
        "This hosted portfolio version uses synthetic real-estate "
        "data and public-safe knowledge artifacts. Private MLS data "
        "and production credentials are not included."
    )


# =====================================================================
# Header
# =====================================================================

st.title("🏠 Real Estate Agentic Copilot")

st.markdown(
    """
    **An agentic real-estate intelligence system combining structured
    search, market analytics, hybrid retrieval, grounded RAG, and
    multi-capability orchestration.**
    """
)

st.info(
    "Portfolio Demo — This public deployment uses synthetic "
    "real-estate data and public-safe knowledge sources. "
    "Production integrations and private data sources are "
    "intentionally disabled."
)


# =====================================================================
# Architecture snapshot
# =====================================================================

st.markdown("### System at a Glance")

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    st.metric(
        "Capabilities",
        "5",
        help=(
            "Search, market analysis, recommendation, "
            "knowledge RAG, and unified orchestration."
        ),
    )

with metric_col2:
    st.metric(
        "Demo Markets",
        "4",
        help=(
            "Synthetic portfolio data across four "
            "demonstration markets."
        ),
    )

with metric_col3:
    st.metric(
        "Sold Comps",
        "288",
        help=(
            "Deterministically generated synthetic "
            "comparable-sale records."
        ),
    )

with metric_col4:
    st.metric(
        "Retrieval",
        "Hybrid",
        help=(
            "Structured similarity combined with "
            "embedding-based semantic similarity."
        ),
    )


# =====================================================================
# Capability navigation
# =====================================================================

st.divider()

(
    search_tab,
    market_tab,
    similar_tab,
    knowledge_tab,
    unified_tab,
) = st.tabs(
    [
        "🔎 Property Search",
        "📈 Market Intelligence",
        "🏡 Similar Homes",
        "📖 Knowledge Assistant",
        "✨ Unified Copilot",
    ]
)


# =====================================================================
# Property Search
# =====================================================================

with search_tab:
    st.subheader("🔎 Structured Property Search")

    st.caption(
        "Translate natural-language requirements into structured "
        "property filters and ranked recommendations."
    )

    st.info(
        'Example: "Find homes in Irvine under $1.5M."'
    )

    search_query = st.text_input(
        "Describe the home you are looking for",
        value="Find homes in Irvine under $1.5M.",
        key="public_search_query",
    )

    if st.button(
        "Search Properties",
        type="primary",
        key="public_search_button",
    ):
        if not search_query.strip():
            st.warning(
                "Please enter a property search query."
            )

        else:
            try:
                orchestrator = get_public_orchestrator()

                with st.spinner(
                    "Searching synthetic demo listings..."
                ):
                    search_result = orchestrator.invoke(
                        search_query.strip(),
                        session_id=(
                            st.session_state.public_session_id
                        ),
                    )

                st.session_state.latest_public_result = (
                    search_result
                )

                st.session_state.latest_public_query = (
                    search_query.strip()
                )

                if search_result.get("route") != "search":
                    st.warning(
                        "This request was routed to "
                        f"{search_result.get('route', 'unknown')}. "
                        "Try a property-search-specific query."
                    )

                else:
                    render_search_result(
                        search_result
                    )

            except Exception as exc:
                st.error(
                    "The public property search could not "
                    "complete this request."
                )

                with st.expander(
                    "Technical details"
                ):
                    st.code(str(exc))


# =====================================================================
# Market Intelligence
# =====================================================================

with market_tab:
    st.subheader("📈 Market Intelligence")

    st.caption(
        "Analyze synthetic sold comparables and compare recent "
        "market conditions with the previous period."
    )

    st.info(
        'Example: "How is the Irvine housing market trending?"'
    )

    market_query = st.text_input(
        "Ask about a demo housing market",
        value="How is the Irvine housing market trending?",
        key="public_market_query",
    )

    if st.button(
        "Analyze Market",
        type="primary",
        key="public_market_button",
    ):
        if not market_query.strip():
            st.warning(
                "Please enter a market-analysis question."
            )

        else:
            try:
                orchestrator = get_public_orchestrator()

                with st.spinner(
                    "Analyzing synthetic comparable sales..."
                ):
                    market_result = orchestrator.invoke(
                        market_query.strip(),
                        session_id=(
                            st.session_state.public_session_id
                        ),
                    )

                st.session_state.latest_public_result = (
                    market_result
                )

                st.session_state.latest_public_query = (
                    market_query.strip()
                )

                if market_result.get("route") != "market":
                    st.warning(
                        "This request was routed to "
                        f"{market_result.get('route', 'unknown')}. "
                        "Try a market-analysis-specific question."
                    )

                else:
                    render_market_result(
                        market_result
                    )

            except Exception as exc:
                st.error(
                    "The public market analysis could not "
                    "complete this request."
                )

                with st.expander(
                    "Technical details"
                ):
                    st.code(str(exc))


# =====================================================================
# Similar Homes
# =====================================================================

with similar_tab:
    st.subheader("🏡 Hybrid Similar-Home Recommendation")

    st.caption(
        "Find related properties using structured attributes, "
        "semantic embeddings, and sold-comparable evidence."
    )

    st.info(
        "Hybrid retrieval combines explicit property characteristics "
        "with embedding-based semantic similarity."
    )

    reference_options = {
        "DEMO-001 — Irvine Single-Family Home — $1.295M":
            "DEMO-001",
        "DEMO-004 — Irvine Condo — $875K":
            "DEMO-004",
        "DEMO-005 — Irvine Condo — $995K":
            "DEMO-005",
    }

    selected_reference = st.selectbox(
        "Choose a reference property",
        options=list(reference_options.keys()),
        index=0,
        key="public_reference_listing",
    )

    reference_listing_id = reference_options[
        selected_reference
    ]

    st.caption(
        f"Reference Listing ID: {reference_listing_id}"
    )

    if st.button(
        "Find Similar Homes",
        type="primary",
        key="public_similar_button",
    ):
        recommendation_query = (
            "Find similar homes to listing id "
            f"{reference_listing_id}"
        )

        try:
            orchestrator = get_public_orchestrator()

            with st.spinner(
                "Running hybrid similarity retrieval..."
            ):
                recommendation_result = orchestrator.invoke(
                    recommendation_query,
                    session_id=(
                        st.session_state.public_session_id
                    ),
                )

            st.session_state.latest_public_result = (
                recommendation_result
            )

            st.session_state.latest_public_query = (
                recommendation_query
            )

            if (
                recommendation_result.get("route")
                != "recommend"
            ):
                st.warning(
                    "This request was routed to "
                    f"{recommendation_result.get('route', 'unknown')}."
                )

            else:
                render_recommendation_result(
                    recommendation_result
                )

        except Exception as exc:
            st.error(
                "The public recommendation service could not "
                "complete this request."
            )

            with st.expander(
                "Technical details"
            ):
                st.code(str(exc))


# =====================================================================
# Knowledge Assistant
# =====================================================================

with knowledge_tab:
    st.subheader("📖 Grounded Knowledge Assistant")

    st.caption(
        "Retrieve relevant context from a public-safe real-estate "
        "knowledge base and generate a grounded answer."
    )
    st.info(
        'Example: "What does DOM mean in real estate?"'
    )

    knowledge_query = st.text_input(
        "Ask a real-estate knowledge question",
        value="What does DOM mean in real estate?",
        key="public_knowledge_query",
    )

    if st.button(
        "Ask Knowledge Assistant",
        type="primary",
        key="public_knowledge_button",
    ):
        if not knowledge_query.strip():
            st.warning(
                "Please enter a real-estate question."
            )

        else:
            try:
                orchestrator = get_public_orchestrator()

                with st.spinner(
                    "Retrieving public-safe knowledge..."
                ):
                    knowledge_result = orchestrator.invoke(
                        knowledge_query.strip(),
                        session_id=(
                            st.session_state.public_session_id
                        ),
                    )

                st.session_state.latest_public_result = (
                    knowledge_result
                )

                st.session_state.latest_public_query = (
                    knowledge_query.strip()
                )

                if (
                    knowledge_result.get("route")
                    != "knowledge"
                ):
                    st.warning(
                        "This request was routed to "
                        f"{knowledge_result.get('route', 'unknown')}. "
                        "Try a real-estate knowledge question."
                    )

                else:
                    render_knowledge_result(
                        knowledge_result
                    )

            except Exception as exc:
                st.error(
                    "The public knowledge assistant could not "
                    "complete this request."
                )

                with st.expander(
                    "Technical details"
                ):
                    st.code(str(exc))

# =====================================================================
# Unified Copilot
# =====================================================================

# =====================================================================
# Unified Copilot
# =====================================================================

with unified_tab:
    st.subheader("✨ Unified Agentic Copilot")

    st.caption(
        "Automatically route a natural-language request to one "
        "or more specialized capabilities through the LangGraph "
        "orchestration layer."
    )

    st.info(
        'Try: "Find homes in Irvine under $1.7M and tell me '
        'about the local market."'
    )

    unified_query = st.text_area(
        "Ask the Unified Copilot",
        value=(
            "Find homes in Irvine under $1.7M and tell me "
            "about the local market."
        ),
        height=100,
        key="public_unified_query",
    )

    example_col1, example_col2, example_col3 = st.columns(3)

    with example_col1:
        st.caption(
            "🔎 Search\n\n"
            "Find homes in Irvine under $1.5M."
        )

    with example_col2:
        st.caption(
            "📈 Market\n\n"
            "How is the Irvine housing market trending?"
        )

    with example_col3:
        st.caption(
            "✨ Mixed Intent\n\n"
            "Find homes in Irvine under $1.7M and tell me "
            "about the local market."
        )

    if st.button(
        "Run Agentic Copilot",
        type="primary",
        key="public_unified_button",
    ):
        if not unified_query.strip():
            st.warning(
                "Please enter a request for the copilot."
            )

        else:
            try:
                orchestrator = get_public_orchestrator()

                with st.spinner(
                    "Routing request and running specialized agents..."
                ):
                    unified_result = orchestrator.invoke(
                        unified_query.strip(),
                        session_id=(
                            st.session_state.public_session_id
                        ),
                    )

                st.session_state.latest_public_result = (
                    unified_result
                )

                st.session_state.latest_public_query = (
                    unified_query.strip()
                )

                render_unified_result(
                    unified_result
                )

            except Exception as exc:
                st.error(
                    "The Unified Copilot could not complete "
                    "this request."
                )

                with st.expander(
                    "Technical details"
                ):
                    st.code(str(exc))


# =====================================================================
# Footer
# =====================================================================

st.divider()

st.caption(
    "Public portfolio demonstration • Synthetic real-estate data • "
    "Private MLS infrastructure and credentials excluded"
)