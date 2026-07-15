import re
from collections.abc import Iterable

from src.compliance.fair_housing_rules import RED_RULES, YELLOW_RULES
from src.schemas.compliance_schema import (
    CheckTarget,
    ComplianceMatch,
    ComplianceReport,
    RiskLevel,
)


class ComplianceAgent:
    """
    Rule-based Fair Housing guardrail for user queries and generated text.

    This agent provides a conservative engineering safeguard. It is not
    a substitute for legal review or a complete compliance program.
    """

    RULE_VERSION = "fair-housing-rules-v1"

    SAFE_REWRITE_MESSAGE = (
        "I can help search using objective property criteria such as city, "
        "price, bedrooms, bathrooms, property type, square footage, commute "
        "preferences, amenities, and user-selected public data."
    )

    REFUSAL_MESSAGE = (
        "I can’t help select or exclude housing based on protected personal "
        "characteristics. I can help refine the search using objective "
        "property features, price, location, commute, amenities, or other "
        "neutral criteria."
    )

    def check_query(self, query: str) -> ComplianceReport:
        """Check an incoming user property-search query."""
        return self._check_text(text=query, target="query")

    def check_output(self, output: str) -> ComplianceReport:
        """Check generated recommendations or explanations."""
        return self._check_text(text=output, target="output")

    def run(
        self,
        text: str,
        target: CheckTarget = "query",
    ) -> ComplianceReport:
        """
        General entry point compatible with an agent workflow.
        """
        return self._check_text(text=text, target=target)

    def _check_text(
        self,
        text: str,
        target: CheckTarget,
    ) -> ComplianceReport:
        normalized_text = self._normalize_text(text)

        red_matches = self._find_matches(
            text=normalized_text,
            rules=RED_RULES,
            risk_level="red",
        )

        yellow_matches = self._find_matches(
            text=normalized_text,
            rules=YELLOW_RULES,
            risk_level="yellow",
        )

        all_matches = [*red_matches, *yellow_matches]

        if red_matches:
            return ComplianceReport(
                target=target,
                original_text=text,
                risk_level="red",
                is_compliant=False,
                should_block=True,
                matched_categories=self._unique_categories(all_matches),
                matches=all_matches,
                safe_rewrite=self.SAFE_REWRITE_MESSAGE,
                refusal_message=self.REFUSAL_MESSAGE,
                rule_version=self.RULE_VERSION,
            )

        if yellow_matches:
            return ComplianceReport(
                target=target,
                original_text=text,
                risk_level="yellow",
                is_compliant=False,
                should_block=False,
                matched_categories=self._unique_categories(yellow_matches),
                matches=yellow_matches,
                safe_rewrite=self._build_yellow_rewrite(
                    categories=self._unique_categories(yellow_matches)
                ),
                rule_version=self.RULE_VERSION,
            )

        return ComplianceReport(
            target=target,
            original_text=text,
            risk_level="green",
            is_compliant=True,
            should_block=False,
            rule_version=self.RULE_VERSION,
        )

    def _find_matches(
        self, 
        text: str, 
        rules: Iterable[dict[str, object]], 
        risk_level: RiskLevel, 
    ) -> list[ComplianceMatch]:
        matches: list[ComplianceMatch] = []

        for rule in rules:
            category = str(rule["category"])
            reason = str(rule["reason"])
            patterns = rule["patterns"]

            if not isinstance(patterns, list):
                continue

            for pattern in patterns:
                match = re.search(str(pattern), text, flags=re.IGNORECASE)

                if match is None:
                    continue

                matches.append(
                    ComplianceMatch(
                        category=category,
                        matched_text=match.group(0),
                        reason=reason,
                        risk_level=risk_level,
                    )
                )

        return matches

    def _build_yellow_rewrite(
        self,
        categories: list[str],
    ) -> str:
        suggestions: list[str] = []

        if "subjective_safety" in categories:
            suggestions.append(
                "use user-selected, objective public safety data"
            )

        if "school_proxy" in categories:
            suggestions.append(
                "use named schools, distance, or published school data"
            )

        if "demographic_steering" in categories:
            suggestions.append(
                "use property features, amenities, commute, and location"
            )

        if not suggestions:
            return self.SAFE_REWRITE_MESSAGE

        return (
            "Please restate the request using neutral criteria. We can "
            + ", ".join(suggestions)
            + "."
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize whitespace while preserving readable matched text."""
        return " ".join(text.strip().split())

    @staticmethod
    def _unique_categories(
        matches: list[ComplianceMatch],
    ) -> list[str]:
        return list(
            dict.fromkeys(match.category for match in matches)
        )