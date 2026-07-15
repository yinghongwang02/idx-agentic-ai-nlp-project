from typing import Any

from src.agents.compliance_agent import ComplianceAgent
from src.agents.explanation_agent import ExplanationAgent
from src.agents.intent_agent import IntentAgent
from src.agents.recommendation_agent import RecommendationAgent
from src.agents.search_agent import SearchAgent
from src.memory.session_memory import SessionMemory
from src.schemas.state_schema import AgentState


class PropertySearchWorkflow:
    """
    End-to-end property-search workflow with session memory and
    Fair Housing compliance guardrails.
    """

    def __init__(
        self,
        search_agent: SearchAgent,
        memory: SessionMemory | None = None,
        compliance_agent: ComplianceAgent | None = None,
        recommendation_agent: RecommendationAgent | None = None,
        explanation_agent: ExplanationAgent | None = None,
    ) -> None:
        self.memory = (
            memory
            if memory is not None
            else SessionMemory()
        )

        self.compliance_agent = (
            compliance_agent
            if compliance_agent is not None
            else ComplianceAgent()
        )

        self.intent_agent = IntentAgent(memory=self.memory)
        self.search_agent = search_agent

        self.recommendation_agent = (
            recommendation_agent
            if recommendation_agent is not None
            else RecommendationAgent()
        )

        self.explanation_agent = (
            explanation_agent
            if explanation_agent is not None
            else ExplanationAgent()
        )

    def run(self, user_query: str) -> AgentState:
        """
        Execute the complete property-search workflow.
        """
        state: AgentState = {
            "user_query": user_query,
            "blocked": False,
            "error": None,
        }

        try:
            state = self._check_query_compliance(state)

            if state["blocked"]:
                return state

            state = self._parse_intent(state)
            state = self._search_properties(state)
            state = self._generate_recommendations(state)
            state = self._generate_explanation(state)
            state = self._check_output_compliance(state)

            return state

        except Exception as exc:
            state["error"] = str(exc)
            state["final_response"] = (
                "The property search could not be completed."
            )
            return state

    def clear_session(self) -> None:
        """Start a completely new property-search session."""
        self.memory.clear()

    def get_memory_snapshot(self) -> dict[str, Any]:
        """Return the current session-memory snapshot."""
        return self.memory.to_dict()

    def _check_query_compliance(
        self,
        state: AgentState,
    ) -> AgentState:
        """
        Check the user query before parsing, storing, or searching.
        """
        report = self.compliance_agent.check_query(
            state["user_query"]
        )

        state["query_compliance"] = report

        if report.should_block:
            state["blocked"] = True
            state["final_response"] = (
                report.refusal_message
                or "This request cannot be processed."
            )

        return state

    def _parse_intent(
        self,
        state: AgentState,
    ) -> AgentState:
        """
        Parse the current query and merge it with session memory.
        """
        intent = self.intent_agent.run(
            state["user_query"]
        )

        state["intent"] = intent
        state["memory_snapshot"] = self.memory.to_dict()

        return state

    def _search_properties(
        self,
        state: AgentState,
    ) -> AgentState:
        """
        Search listings using the memory-enriched PropertyIntent.
        """
        intent = state["intent"]

        search_results = self.search_agent.run(intent)

        state["search_results"] = search_results

        return state

    def _generate_recommendations(
        self,
        state: AgentState,
    ) -> AgentState:
        """
        Rank the retrieved listings.
        """
        search_results = state.get("search_results", [])

        recommendations = self.recommendation_agent.run(
            search_results
        )

        state["recommendations"] = recommendations

        return state

    def _generate_explanation(
        self,
        state: AgentState,
    ) -> AgentState:
        """
        Generate the user-facing recommendation explanation.
        """
        recommendations = state.get("recommendations", [])

        explanation = self.explanation_agent.run(
            state["intent"],
            recommendations,
        )

        state["explanation"] = explanation

        return state

    def _check_output_compliance(
        self,
        state: AgentState,
    ) -> AgentState:
        """
        Screen generated output before returning it to the user.
        """
        explanation = state.get("explanation", "")

        report = self.compliance_agent.check_output(
            explanation
        )

        state["output_compliance"] = report

        if report.risk_level == "red":
            state["blocked"] = True
            state["final_response"] = (
                report.refusal_message
                or report.safe_rewrite
                or "The generated response was blocked."
            )
            return state

        if report.risk_level == "yellow":
            state["final_response"] = (
                report.safe_rewrite
                or self.compliance_agent.SAFE_REWRITE_MESSAGE
            )
            return state

        query_report = state.get("query_compliance")

        if (
            query_report is not None
            and query_report.risk_level == "yellow"
        ):
            notice = (
                "I’m using only neutral, objective property criteria "
                "for this search and am not using demographic "
                "characteristics or subjective neighborhood labels."
            )

            state["final_response"] = (
                f"{notice}\n\n{explanation}"
            )
        else:
            state["final_response"] = explanation

        return state