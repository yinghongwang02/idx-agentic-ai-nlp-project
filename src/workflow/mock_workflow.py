from src.agents.intent_agent import IntentAgent
from src.agents.search_agent import SearchAgent
from src.agents.compliance_agent import ComplianceAgent
from src.agents.recommendation_agent import RecommendationAgent
from src.agents.explanation_agent import ExplanationAgent
from src.schemas.state_schema import AgentState

from src.agents.search_agent import SearchAgent
from src.search.csv_search_repository import CSVSearchRepository


def run_mock_workflow(user_query: str) -> str:
    state: AgentState = {
        "user_query": user_query,
    }

    intent_agent = IntentAgent()
    # search_agent = SearchAgent()
    search_repository = CSVSearchRepository("data/sample_listings.csv")
    search_agent = SearchAgent(repository=search_repository)

    compliance_agent = ComplianceAgent()
    recommendation_agent = RecommendationAgent()
    explanation_agent = ExplanationAgent()

    state["intent"] = intent_agent.run(state["user_query"])
    state["listings"] = search_agent.run(state["intent"])
    state["compliance_status"] = compliance_agent.run(state["user_query"])
    state["recommendations"] = recommendation_agent.run(state["listings"])
    state["final_answer"] = explanation_agent.run(state["intent"], state["recommendations"])

    return (
        f"Compliance status: {state['compliance_status']}\n\n"
        f"Parsed intent: {state['intent'].model_dump()}\n\n"
        f"{state['final_answer']}"
    )