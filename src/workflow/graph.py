from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from src.agents.compliance_agent import ComplianceAgent
from src.agents.explanation_agent import ExplanationAgent
from src.agents.intent_agent import IntentAgent
from src.agents.recommendation_agent import RecommendationAgent
from src.agents.search_agent import SearchAgent
from src.memory.session_memory import SessionMemory
from src.schemas.state_schema import AgentState


class PropertySearchGraph:
    """
    LangGraph-based property search workflow with session memory
    and Fair Housing compliance guardrails.
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

        self.graph = self._build_graph()


    def _build_graph(self):
        """
        Build and compile the LangGraph workflow.
        """
        builder = StateGraph(AgentState)

        builder.add_node(
            "query_compliance",
            self._check_query_compliance,
        )

        builder.add_node(
            "parse_intent",
            self._parse_intent,
        )

        builder.add_node(
            "search",
            self._search_properties,
        )

        builder.add_node(
            "recommend",
            self._generate_recommendations,
        )

        builder.add_node(
            "explain",
            self._generate_explanation,
        )

        builder.add_node(
            "output_compliance",
            self._check_output_compliance,
        )

        builder.add_edge(
            START,
            "query_compliance",
        )

        builder.add_conditional_edges(
            "query_compliance",
            self._route_after_query_compliance,
            {
                "continue": "parse_intent",
                "blocked": END,
            },
        )

        builder.add_edge(
            "parse_intent",
            "search",
        )

        builder.add_edge(
            "search",
            "recommend",
        )

        builder.add_edge(
            "recommend",
            "explain",
        )

        builder.add_edge(
            "explain",
            "output_compliance",
        )

        builder.add_edge(
            "output_compliance",
            END,
        )

        return builder.compile()


    def run(
        self,
        user_query: str,
    ) -> AgentState:
        """
        Execute one LangGraph workflow turn.
        """
        initial_state: AgentState = {
            "user_query": user_query,
            "blocked": False,
            "error": None,
        }

        try:
            result = self.graph.invoke(initial_state)

            return result

        except Exception as exc:
            initial_state["error"] = str(exc)
            initial_state["final_response"] = (
                "The property search could not be completed."
            )

            return initial_state
        

    def clear_session(self) -> None:
        self.memory.clear()

    def get_memory_snapshot(self) -> dict[str, Any]:
        return self.memory.to_dict()
    

    @staticmethod
    def _route_after_query_compliance(
        state: AgentState,
    ) -> Literal["continue", "blocked"]:
        """
        Route blocked queries directly to END.

        Safe and non-blocking queries continue to intent parsing.
        """
        if state.get("blocked", False):
            return "blocked"

        return "continue"
    

    def _check_query_compliance(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        report = self.compliance_agent.check_query(
            state["user_query"]
        )

        updates: dict[str, Any] = {
            "query_compliance": report,
        }

        if report.should_block:
            updates["blocked"] = True
            updates["final_response"] = (
                report.refusal_message
                or "This request cannot be processed."
            )

        return updates
    

    def _parse_intent(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        intent = self.intent_agent.run(
            state["user_query"]
        )

        return {
            "intent": intent,
            "memory_snapshot": self.memory.to_dict(),
        }
    

    def _search_properties(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        search_results = self.search_agent.run(
            state["intent"]
        )

        return {
            "search_results": search_results,
        }
    

    def _generate_recommendations(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        recommendations = self.recommendation_agent.run(
            state.get("search_results", [])
        )

        return {
            "recommendations": recommendations,
        }


    def _generate_explanation(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        explanation = self.explanation_agent.run(
            state["intent"],
            state.get("recommendations", []),
        )

        return {
            "explanation": explanation,
        }
    

    def _check_output_compliance(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        explanation = state.get("explanation", "")

        report = self.compliance_agent.check_output(
            explanation
        )

        updates: dict[str, Any] = {
            "output_compliance": report,
        }

        if report.risk_level == "red":
            updates["blocked"] = True
            updates["final_response"] = (
                report.refusal_message
                or report.safe_rewrite
                or "The generated response was blocked."
            )

            return updates

        if report.risk_level == "yellow":
            updates["final_response"] = (
                report.safe_rewrite
                or self.compliance_agent.SAFE_REWRITE_MESSAGE
            )

            return updates

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

            updates["final_response"] = (
                f"{notice}\n\n{explanation}"
            )

        else:
            updates["final_response"] = explanation

        return updates
    



