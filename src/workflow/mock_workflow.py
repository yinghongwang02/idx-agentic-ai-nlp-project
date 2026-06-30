from src.agents.intent_agent import IntentAgent
from src.agents.search_agent import SearchAgent
from src.agents.compliance_agent import ComplianceAgent
from src.agents.recommendation_agent import RecommendationAgent
from src.agents.explanation_agent import ExplanationAgent


def run_mock_workflow(user_query: str) -> str:
    intent_agent = IntentAgent()
    search_agent = SearchAgent()
    compliance_agent = ComplianceAgent()
    recommendation_agent = RecommendationAgent()
    explanation_agent = ExplanationAgent()

    intent = intent_agent.run(user_query)
    listings = search_agent.run(intent)
    compliance_status = compliance_agent.run(user_query)
    recommendations = recommendation_agent.run(listings)
    final_answer = explanation_agent.run(recommendations)

    return (
        f"Compliance status: {compliance_status}\n\n"
        f"Parsed intent: {intent.model_dump()}\n\n"
        f"{final_answer}"
    )