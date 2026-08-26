from __future__ import annotations

import re

from src.schemas.orchestrator_state_schema import (
    RouterDecision,
)


class IntentRouter:
    """
    Lightweight deterministic router for top-level real-estate capabilities.

    Supported handbook routes:

        search
        market
        recommend
        knowledge
        mixed

    The router performs classification only.

    It does not:
        - query databases
        - execute agents
        - parse full PropertyIntent objects
        - call an LLM
        - generate user-facing answers
    """

    # -----------------------------------------------------------------
    # Search signals
    # -----------------------------------------------------------------

    SEARCH_PATTERNS = (
        r"\bfind\b.*\b(home|homes|house|houses|property|properties|"
        r"condo|condos|townhouse|townhouses|listing|listings)\b",

        r"\bshow\s+me\b.*\b(home|homes|house|houses|property|properties|"
        r"condo|condos|townhouse|townhouses|listing|listings)\b",

        r"\bsearch\b.*\b(home|homes|house|houses|property|properties|"
        r"listing|listings)\b",

        r"\blooking\s+for\b.*\b(home|homes|house|houses|property|properties|"
        r"condo|condos|townhouse|townhouses)\b",

        r"\b(home|homes|house|houses|property|properties|"
        r"condo|condos|townhouse|townhouses)\b"
        r".*\b(under|below|less than|up to|max|budget)\b",

        r"\b\d+\s*[- ]?\s*(bed|beds|bedroom|bedrooms)\b",

        r"\b\d+(?:\.5)?\s*[- ]?\s*(bath|baths|bathroom|bathrooms)\b",
    )

    SEARCH_TERMS = {
        "garage",
        "pool",
        "backyard",
        "yard",
        "patio",
        "balcony",
        "fireplace",
        "ocean view",
        "mountain view",
        "open floor plan",
        "single family",
        "townhouse",
        "condo",
    }

    # -----------------------------------------------------------------
    # Market signals
    # -----------------------------------------------------------------

    MARKET_PATTERNS = (
        r"\bmarket\b",

        r"\bmarket\s+trend\b",

        r"\bprices?\s+(?:(?:are|is)\s+)?"
        r"(rising|falling|increasing|decreasing|going\s+up|going\s+down)\b",

        r"\b(home|housing|property)\s+prices?\b",

        r"\bmedian\s+(sale|sold|close|closing|home|house|property)?\s*price\b",

        r"\baverage\s+days\s+on\s+market\b",

        r"\bmedian\s+days\s+on\s+market\b",

        r"\bdays\s+on\s+market\b",

        r"\bsale[- ]to[- ]list\b",

        r"\bprice\s+per\s+(square\s+foot|sqft)\b",

        r"\bppsf\b",

        r"\bwarming\b",

        r"\bcooling\b",

        r"\bmarket\s+(warming|cooling|stable)\b",

        r"\bsold\s+(comps|comparables|properties|homes)\b",
    )

    MARKET_TERMS = {
        "market stats",
        "market statistics",
        "market conditions",
        "market activity",
        "price trend",
        "price trends",
        "recent sales",
        "recent sold",
    }

    # -----------------------------------------------------------------
    # Similar-home recommendation signals
    # -----------------------------------------------------------------

    RECOMMEND_PATTERNS = (
        r"\bsimilar\s+(home|homes|house|houses|property|properties|"
        r"listing|listings)\b",

        r"\b(home|homes|house|houses|property|properties|listing|listings)"
        r"\s+similar\s+to\b",

        r"\bmore\s+like\s+this\b",

        r"\bproperties?\s+like\s+this\b",

        r"\bhomes?\s+like\s+this\b",

        r"\bhouses?\s+like\s+this\b",

        r"\bsimilar\s+to\s+(this|listing)\b",

        r"\brecommend\s+similar\b",

        r"\bfind\s+similar\b",

        r"\balternatives?\s+(to|similar\s+to)\b",
    )

    # -----------------------------------------------------------------
    # Knowledge / RAG signals
    # -----------------------------------------------------------------

    KNOWLEDGE_PATTERNS = (
        r"\bwhat\s+does\b.+\bmean\b",

        r"\bwhat\s+is\s+the\s+meaning\s+of\b",

        r"\bdefine\b",

        r"\bdefinition\s+of\b",

        r"\bexplain\s+(the\s+)?(field|term|meaning|concept)\b",

        r"\bwhat\s+does\s+[a-z0-9_]+\s+stand\s+for\b",

        r"\bhow\s+is\b.+\bdefined\b",
    )

    KNOWLEDGE_TERMS = {
        "mls field",
        "mls fields",
        "field definition",
        "field mapping",
        "daysonmarket",
        "closeprice",
        "closedate",
        "listingkey",
        "l_systemprice",
        "bedroomstotal",
        "livingarea",
        "associationfee",
        "property subtype",
        "propertysubtype",
    }

    # -----------------------------------------------------------------
    # Construction
    # -----------------------------------------------------------------

    def route(
        self,
        query: str,
    ) -> RouterDecision:
        """
        Classify a user query into one top-level orchestration route.
        """

        normalized_query = self._normalize_query(
            query
        )

        if not normalized_query:
            return RouterDecision(
                route="knowledge",
                routes=["knowledge"],
                reason=(
                    "Empty input reached the router; "
                    "defaulted to the safest non-transactional route."
                ),
            )

        has_recommend = self._is_recommend(
            normalized_query
        )

        has_market = self._is_market(
            normalized_query
        )

        has_search = self._is_search(
            normalized_query
        )

        has_knowledge = self._is_knowledge(
            normalized_query
        )

        # -------------------------------------------------------------
        # Recommendation takes precedence over ordinary search language
        # when the query clearly asks for listing-to-listing similarity.
        # -------------------------------------------------------------

        if has_recommend:
            return RouterDecision(
                route="recommend",
                routes=["recommend"],
                reason=(
                    "Detected listing-to-listing similar-home "
                    "recommendation intent."
                ),
            )

        # -------------------------------------------------------------
        # Handbook mixed intent:
        #
        # "Find me affordable homes in Pasadena and tell me whether
        # prices are rising."
        #
        # Search + Market are both independently executable.
        # -------------------------------------------------------------

        if has_search and has_market:
            return RouterDecision(
                route="mixed",
                routes=[
                    "search",
                    "market",
                ],
                reason=(
                    "Detected both property-search and market-analysis "
                    "intent."
                ),
            )

        if has_market:
            return RouterDecision(
                route="market",
                routes=["market"],
                reason=(
                    "Detected standalone market statistics or "
                    "market-trend intent."
                ),
            )

        if has_knowledge:
            return RouterDecision(
                route="knowledge",
                routes=["knowledge"],
                reason=(
                    "Detected real-estate terminology, field-definition, "
                    "or conceptual knowledge intent."
                ),
            )

        if has_search:
            return RouterDecision(
                route="search",
                routes=["search"],
                reason=(
                    "Detected property-search criteria or listing-search "
                    "intent."
                ),
            )

        # -------------------------------------------------------------
        # Safe deterministic fallback
        #
        # For Week 9 we keep the public route contract limited to the
        # five handbook routes instead of introducing an extra
        # "unknown" route.
        #
        # Knowledge is the least side-effecting capability and can
        # produce an evidence-based fallback response.
        # -------------------------------------------------------------

        return RouterDecision(
            route="knowledge",
            routes=["knowledge"],
            reason=(
                "No strong search, market, or recommendation signal "
                "was detected; defaulted to the knowledge route."
            ),
        )

    # -----------------------------------------------------------------
    # Intent detectors
    # -----------------------------------------------------------------

    @classmethod
    def _is_search(
        cls,
        query: str,
    ) -> bool:
        if cls._matches_any(
            query=query,
            patterns=cls.SEARCH_PATTERNS,
        ):
            return True

        return any(
            term in query
            for term in cls.SEARCH_TERMS
        )

    @classmethod
    def _is_market(
        cls,
        query: str,
    ) -> bool:
        if cls._matches_any(
            query=query,
            patterns=cls.MARKET_PATTERNS,
        ):
            return True

        return any(
            term in query
            for term in cls.MARKET_TERMS
        )

    @classmethod
    def _is_recommend(
        cls,
        query: str,
    ) -> bool:
        return cls._matches_any(
            query=query,
            patterns=cls.RECOMMEND_PATTERNS,
        )

    @classmethod
    def _is_knowledge(
        cls,
        query: str,
    ) -> bool:
        if cls._matches_any(
            query=query,
            patterns=cls.KNOWLEDGE_PATTERNS,
        ):
            return True

        return any(
            term in query
            for term in cls.KNOWLEDGE_TERMS
        )

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _matches_any(
        query: str,
        patterns: tuple[str, ...],
    ) -> bool:
        return any(
            re.search(
                pattern,
                query,
                flags=re.IGNORECASE,
            )
            is not None
            for pattern in patterns
        )

    @staticmethod
    def _normalize_query(
        query: str,
    ) -> str:
        return " ".join(
            str(query or "")
            .strip()
            .lower()
            .split()
        )