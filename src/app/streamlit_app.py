from datetime import datetime

import streamlit as st

from src.agents.search_agent import SearchAgent
from src.search.mysql_search_repository import (
    MySQLSearchRepository,
)
from src.workflow.graph import PropertySearchGraph


def create_workflow() -> PropertySearchGraph:
    repository = MySQLSearchRepository()

    search_agent = SearchAgent(
        repository=repository
    )

    return PropertySearchGraph(
        search_agent=search_agent
    )


st.set_page_config(
    page_title="Real Estate Agentic Copilot",
    page_icon="🏠",
    layout="wide",
)


if "workflow" not in st.session_state:
    st.session_state.workflow = (
        create_workflow()
    )


if "search_history" not in st.session_state:
    st.session_state.search_history = []


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


st.title(
    "🏠 Real Estate Agentic Copilot"
)

st.caption(
    "Multi-turn property search powered by "
    "LangGraph, session memory, MySQL, and "
    "compliance guardrails."
)


query = st.text_input(
    "Enter a property search query",
    placeholder=(
        "Try: Find townhouses in Irvine, "
        "then follow up with: Under 1.2 million"
    ),
)


if st.button("Search"):
    if not query.strip():
        st.warning(
            "Please enter a search query."
        )

    else:
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
            intent = state.get("intent")

            recommendations = state.get(
                "recommendations",
                [],
            )

            top_listing = None

            if recommendations:
                first_listing = (
                    recommendations[0]
                )

                top_listing = (
                    first_listing.listing_id
                    or first_listing.listing_key
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
                    "top_listing": top_listing,
                },
            )

            st.session_state.search_history = (
                st.session_state.search_history[:5]
            )

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

        intent = state.get("intent")

        if intent is not None:
            st.subheader(
                "Parsed Intent"
            )

            with st.expander(
                "View structured search intent"
            ):
                st.json(
                    intent.model_dump()
                )

        recommendations = state.get(
            "recommendations",
            [],
        )

        if not state.get("blocked"):
            st.subheader(
                "Top Recommendations"
            )

            if not recommendations:
                st.info(
                    "No matching listings found."
                )

            else:
                for listing in recommendations:
                    with st.container(
                        border=True
                    ):
                        listing_name = (
                            listing.listing_id
                            or listing.listing_key
                        )

                        st.markdown(
                            f"### {listing_name}"
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

                        st.write(
                            f"**Remarks:** "
                            f"{listing.public_remarks}"
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