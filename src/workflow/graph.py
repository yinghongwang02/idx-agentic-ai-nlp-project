from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from src.workflow.property_analysis_subgraph import (
    PropertyAnalysisSubgraph,
)

from src.agents.comparable_value_agent import ComparableValueAgent
from src.agents.compliance_agent import ComplianceAgent
from src.agents.explanation_agent import ExplanationAgent
from src.agents.intent_agent import IntentAgent
from src.agents.market_agent import MarketAgent
from src.agents.negotiation_agent import NegotiationAgent
from src.agents.preference_match_agent import PreferenceMatchAgent
from src.agents.recommendation_agent import RecommendationAgent
from src.agents.search_agent import SearchAgent
from src.memory.session_memory import SessionMemory
from src.schemas.state_schema import AgentState
from src.search.mysql_sold_comp_repository import MySQLSoldCompRepository

from src.schemas.intent_schema import PropertyIntent
from src.schemas.listing_schema import ListingSchema
from src.schemas.recommendation_score_schema import RecommendationScore

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

class PropertySearchGraph:
    """
    LangGraph-based property search workflow with session memory,
    Fair Housing compliance guardrails, market analysis, and
    multi-signal property recommendation scoring.
    """

    SEARCH_CANDIDATE_LIMIT = 50
    RECOMMENDATION_LIMIT = 5

    DEFAULT_MAX_PARALLEL_CANDIDATES = 4

    def __init__(
        self,
        search_agent: SearchAgent,
        memory: SessionMemory | None = None,
        compliance_agent: ComplianceAgent | None = None,
        market_agent: MarketAgent | None = None,
        preference_match_agent: PreferenceMatchAgent | None = None,
        comparable_value_agent: ComparableValueAgent | None = None,
        negotiation_agent: NegotiationAgent | None = None,
        recommendation_agent: RecommendationAgent | None = None,
        explanation_agent: ExplanationAgent | None = None,
        parallel_candidate_analysis: bool = True,
        max_parallel_candidates: int = (
            DEFAULT_MAX_PARALLEL_CANDIDATES
        ),
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

        self.intent_agent = IntentAgent(
            memory=self.memory
        )

        self.search_agent = search_agent

        if max_parallel_candidates < 1:
            raise ValueError(
                "max_parallel_candidates must be at least 1."
            )

        self.parallel_candidate_analysis = (
            parallel_candidate_analysis
        )

        self.max_parallel_candidates = (
            max_parallel_candidates
        )

        self.market_agent = (
            market_agent
            if market_agent is not None
            else MarketAgent(
                repository=MySQLSoldCompRepository()
            )
        )

        self.preference_match_agent = (
            preference_match_agent
            if preference_match_agent is not None
            else PreferenceMatchAgent()
        )

        self.comparable_value_agent = (
            comparable_value_agent
            if comparable_value_agent is not None
            else ComparableValueAgent()
        )

        self.negotiation_agent = (
            negotiation_agent
            if negotiation_agent is not None
            else NegotiationAgent()
        )

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

        self.property_analysis_subgraph = (
            PropertyAnalysisSubgraph(
                market_agent=self.market_agent,
                preference_match_agent=(
                    self.preference_match_agent
                ),
                comparable_value_agent=(
                    self.comparable_value_agent
                ),
                negotiation_agent=self.negotiation_agent,
                recommendation_agent=self.recommendation_agent,
            )
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
            "property_analysis",
            self._analyze_properties,
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
            "property_analysis",
        )

        builder.add_edge(
            "property_analysis",
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
            result = self.graph.invoke(
                initial_state
            )

            return result

        except Exception as exc:
            initial_state["error"] = str(exc)
            initial_state["final_response"] = (
                "The property search could not be completed."
            )

            return initial_state

    def clear_session(self) -> None:
        self.memory.clear()

    def get_memory_snapshot(
        self,
    ) -> dict[str, Any]:
        return self.memory.to_dict()

    @staticmethod
    def _route_after_query_compliance(
        state: AgentState,
    ) -> Literal["continue", "blocked"]:
        """
        Route blocked queries directly to END.

        Safe and non-blocking queries continue to intent parsing.
        """
        if state.get(
            "blocked",
            False,
        ):
            return "blocked"

        return "continue"

    def _check_query_compliance(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        report = (
            self.compliance_agent.check_query(
                state["user_query"]
            )
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
            "memory_snapshot": (
                self.memory.to_dict()
            ),
        }

    def _search_properties(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        """
        Retrieve a larger candidate pool for downstream reranking.
        """
        search_results = (
            self.search_agent.run(
                state["intent"],
                limit=self.SEARCH_CANDIDATE_LIMIT,
            )
        )

        return {
            "search_results": search_results,
        }

    def _analyze_single_candidate(
        self,
        listing: ListingSchema,
        intent: PropertyIntent,
    ) -> RecommendationScore:
        """
        Analyze one candidate listing through the reusable property
        analysis subgraph.
        """
        analysis_result = (
            self.property_analysis_subgraph.run(
                listing=listing,
                intent=intent,
            )
        )

        recommendation = analysis_result.get(
            "recommendation"
        )

        if recommendation is None:
            raise ValueError(
                "Property analysis completed without producing "
                "a recommendation."
            )

        return recommendation

    def _analyze_candidates_sequentially(
        self,
        listings: list[ListingSchema],
        intent: PropertyIntent,
    ) -> tuple[
        list[RecommendationScore],
        list[dict[str, str]],
    ]:
        """
        Analyze candidates sequentially.

        This path is retained for benchmarking, regression testing,
        and fallback behavior.
        """
        recommendations: list[
            RecommendationScore
        ] = []

        errors: list[dict[str, str]] = []

        for listing in listings:
            try:
                recommendation = (
                    self._analyze_single_candidate(
                        listing=listing,
                        intent=intent,
                    )
                )

                recommendations.append(
                    recommendation
                )

            except Exception as exc:
                errors.append(
                    {
                        "listing_key": (
                            listing.listing_key
                        ),
                        "error": str(exc),
                    }
                )

        return recommendations, errors

    def _analyze_candidates_in_parallel(
        self,
        listings: list[ListingSchema],
        intent: PropertyIntent,
    ) -> tuple[
        list[RecommendationScore],
        list[dict[str, str]],
    ]:
        """
        Analyze candidate listings concurrently using bounded
        thread-based parallelism.

        Individual candidate failures are isolated so successful
        candidates can still be ranked.
        """
        if not listings:
            return [], []

        worker_count = min(
            self.max_parallel_candidates,
            len(listings),
        )

        recommendations: list[
            RecommendationScore
        ] = []

        errors: list[dict[str, str]] = []

        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix=(
                "candidate-property-analysis"
            ),
        ) as executor:
            future_to_listing = {
                executor.submit(
                    self._analyze_single_candidate,
                    listing,
                    intent,
                ): listing
                for listing in listings
            }

            for future in as_completed(
                future_to_listing
            ):
                listing = future_to_listing[
                    future
                ]

                try:
                    recommendation = (
                        future.result()
                    )

                    recommendations.append(
                        recommendation
                    )

                except Exception as exc:
                    errors.append(
                        {
                            "listing_key": (
                                listing.listing_key
                            ),
                            "error": str(exc),
                        }
                    )

        return recommendations, errors

    def _analyze_properties(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        """
        Analyze candidate listings using either bounded parallel
        execution or the retained sequential path, then rank the
        successful recommendation results.
        """
        intent = state["intent"]

        search_results = state.get(
            "search_results",
            [],
        )

        if self.parallel_candidate_analysis:
            (
                scored_recommendations,
                analysis_errors,
            ) = self._analyze_candidates_in_parallel(
                listings=search_results,
                intent=intent,
            )

        else:
            (
                scored_recommendations,
                analysis_errors,
            ) = (
                self._analyze_candidates_sequentially(
                    listings=search_results,
                    intent=intent,
                )
            )

        recommendations = (
            self.recommendation_agent.rank(
                recommendations=(
                    scored_recommendations
                ),
                limit=self.RECOMMENDATION_LIMIT,
            )
        )

        return {
            "recommendations": recommendations,
            "candidate_analysis_errors": (
                analysis_errors
            ),
        }

    def _generate_explanation(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        """
        Generate a recommendation explanation directly from
        ranked RecommendationScore objects.
        """
        explanation = (
            self.explanation_agent.run(
                state["intent"],
                state.get(
                    "recommendations",
                    [],
                ),
            )
        )

        return {
            "explanation": explanation,
        }
    
    def _check_output_compliance(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        explanation = state.get(
            "explanation",
            "",
        )

        report = (
            self.compliance_agent.check_output(
                explanation
            )
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
                or self.compliance_agent
                .SAFE_REWRITE_MESSAGE
            )

            return updates

        query_report = state.get(
            "query_compliance"
        )

        if (
            query_report is not None
            and query_report.risk_level
            == "yellow"
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
            updates["final_response"] = (
                explanation
            )

        return updates