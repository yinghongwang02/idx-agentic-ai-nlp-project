import streamlit as st

from src.agents.compliance_agent import ComplianceAgent
from src.agents.explanation_agent import ExplanationAgent
from src.agents.intent_agent import IntentAgent
from src.agents.recommendation_agent import RecommendationAgent
from src.agents.search_agent import SearchAgent
from src.search.csv_search_repository import CSVSearchRepository
from src.search.mysql_search_repository import MySQLSearchRepository

from datetime import datetime


def run_pipeline(query: str) -> dict:
    intent_agent = IntentAgent()
    compliance_agent = ComplianceAgent()
    # repository = CSVSearchRepository("data/sample_listings.csv")
    repository = MySQLSearchRepository()
    search_agent = SearchAgent(repository=repository)
    recommendation_agent = RecommendationAgent()
    explanation_agent = ExplanationAgent()

    intent = intent_agent.run(query)
    compliance_status = compliance_agent.run(query)
    listings = search_agent.run(intent)
    recommendations = recommendation_agent.run(listings)
    final_answer = explanation_agent.run(intent, recommendations)

    return {
        "intent": intent,
        "compliance_status": compliance_status,
        "recommendations": recommendations,
        "final_answer": final_answer,
    }


st.set_page_config(
    page_title="Real Estate Agentic Copilot",
    page_icon="🏠",
    layout="wide",
)

# Initialize search history
if "search_history" not in st.session_state:
    st.session_state.search_history = []

# sidebar search history
with st.sidebar:
    st.header("🕒 Search History")

    history = st.session_state.search_history

    if not history:
        st.caption("No searches yet.")
    else:
        for item in history:
            title = f"{item['timestamp']} | {item['query']}"

            with st.expander(title):
                st.metric("Matching Listings", item["result_count"])

                if item["top_listing"]:
                    st.write(f"**Top Listing:** {item['top_listing']}")

                st.write("**Parsed Intent**")
                st.json(item["intent"], expanded=False)

st.title("🏠 Real Estate Agentic Copilot")
st.caption("Week 2 Demo: Natural language property search over sample MLS-style listings")

query = st.text_input(
    "Enter a property search query",
    value="Show me 3 bedroom condos in Irvine under 900k",
)

if st.button("Search"):
    if not query.strip():
        st.warning("Please enter a search query.")
    else:
        result = run_pipeline(query)

        top_listing = None
        if result["recommendations"]:
            first_listing = result["recommendations"][0]
            top_listing = first_listing.listing_id or first_listing.listing_key

        # save search history
        st.session_state.search_history.insert(
            0,
            {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "query": query,
                "intent": result["intent"].model_dump(),
                "result_count": len(result["recommendations"]),
                "top_listing": top_listing,
            },
        )

        # Keep only the most recent 5 searches
        st.session_state.search_history = (
            st.session_state.search_history[:5]
        )

        st.subheader("Parsed Intent")
        with st.expander("Parsed Intent"): 
            st.json(result["intent"].model_dump()) # show parsed intent only after expansion

        st.subheader("Compliance Status")
        st.write(result["compliance_status"])

        st.subheader("Top Recommendations")

        recommendations = result["recommendations"]

        if not recommendations:
            st.info("No matching listings found.")
        else:
            for listing in recommendations:
                with st.container(border=True):
                    st.markdown(f"### {listing.listing_id or listing.listing_key}")
                    st.write(f"**Address:** {listing.unparsed_address}")
                    st.write(f"**City:** {listing.city}")
                    st.write(f"**Price:** ${listing.list_price:,.0f}")
                    st.write(
                        f"**Beds/Baths:** "
                        f"{listing.bedrooms_total} bed / "
                        f"{listing.bathrooms_total_integer} bath"
                    )
                    st.write(f"**Living Area:** {listing.living_area:,.0f} sqft")
                    st.write(f"**Days on Market:** {listing.days_on_market}")
                    st.write(f"**Remarks:** {listing.public_remarks}")

        st.subheader("Generated Explanation")
        st.text(result["final_answer"])
