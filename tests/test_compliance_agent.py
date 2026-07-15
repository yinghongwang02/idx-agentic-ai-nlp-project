"""
Regression tests for the current rule-based Fair Housing guardrail.

These tests verify the behavior of the defined rules, risk levels,
blocking logic, safe rewrites, and output screening.

They do not claim exhaustive legal or linguistic coverage.
"""

import pytest

from src.agents.compliance_agent import ComplianceAgent


@pytest.fixture
def compliance_agent() -> ComplianceAgent:
    return ComplianceAgent()


def test_neutral_property_query_is_green(
    compliance_agent: ComplianceAgent,
) -> None:
    report = compliance_agent.check_query(
        "Find townhouses in Irvine under 1.2 million with a garage."
    )

    assert report.target == "query"
    assert report.risk_level == "green"
    assert report.is_compliant is True
    assert report.should_block is False
    assert report.matched_categories == []
    assert report.matches == []
    assert report.safe_rewrite is None
    assert report.refusal_message is None


def test_subjective_safety_and_school_query_is_yellow(
    compliance_agent: ComplianceAgent,
) -> None:
    report = compliance_agent.check_query(
        "Find homes in the safest neighborhood with good schools."
    )

    assert report.target == "query"
    assert report.risk_level == "yellow"
    assert report.is_compliant is False
    assert report.should_block is False

    assert set(report.matched_categories) == {
        "subjective_safety",
        "school_proxy",
    }

    assert len(report.matches) == 2
    assert report.safe_rewrite is not None
    assert report.refusal_message is None


def test_religion_based_housing_request_is_red_and_blocked(
    compliance_agent: ComplianceAgent,
) -> None:
    report = compliance_agent.check_query(
        "Show me homes in a Christian neighborhood."
    )

    assert report.risk_level == "red"
    assert report.is_compliant is False
    assert report.should_block is True
    assert report.matched_categories == ["religion"]

    assert len(report.matches) == 1
    assert report.matches[0].category == "religion"
    assert report.matches[0].risk_level == "red"

    assert report.safe_rewrite is not None
    assert report.refusal_message is not None


def test_familial_status_exclusion_is_red_and_blocked(
    compliance_agent: ComplianceAgent,
) -> None:
    report = compliance_agent.check_query(
        "Find apartments with no children nearby."
    )

    assert report.risk_level == "red"
    assert report.is_compliant is False
    assert report.should_block is True
    assert report.matched_categories == ["familial_status"]

    assert report.safe_rewrite is not None
    assert report.refusal_message is not None


def test_property_description_does_not_trigger_false_positive(
    compliance_agent: ComplianceAgent,
) -> None:
    report = compliance_agent.check_query(
        "I want a single-family home with white kitchen cabinets."
    )

    assert report.risk_level == "green"
    assert report.is_compliant is True
    assert report.should_block is False
    assert report.matched_categories == []


def test_generated_output_with_demographic_steering_is_yellow(
    compliance_agent: ComplianceAgent,
) -> None:
    report = compliance_agent.check_output(
        "This property is ideal because the neighborhood is mostly "
        "young professionals."
    )

    assert report.target == "output"
    assert report.risk_level == "yellow"
    assert report.is_compliant is False
    assert report.should_block is False
    assert report.matched_categories == ["demographic_steering"]

    assert len(report.matches) == 1
    assert report.matches[0].matched_text == (
        "neighborhood is mostly young professionals"
    )

    assert report.safe_rewrite is not None
    assert report.refusal_message is None


def test_run_supports_query_target(
    compliance_agent: ComplianceAgent,
) -> None:
    report = compliance_agent.run(
        text="Find condos in Pasadena.",
        target="query",
    )

    assert report.target == "query"
    assert report.risk_level == "green"


def test_run_supports_output_target(
    compliance_agent: ComplianceAgent,
) -> None:
    report = compliance_agent.run(
        text="The home includes a remodeled kitchen and private garage.",
        target="output",
    )

    assert report.target == "output"
    assert report.risk_level == "green"


def test_report_contains_rule_version(
    compliance_agent: ComplianceAgent,
) -> None:
    report = compliance_agent.check_query(
        "Find condos in Irvine."
    )

    assert report.rule_version == "fair-housing-rules-v1"


@pytest.mark.parametrize(
    ("query", "expected_category"),
    [
        ("Show me homes in a Christian neighborhood.", "religion"),
        ("Find apartments with no children nearby.", "familial_status"),
        ("I want an American-only neighborhood.", "national_origin"),
        ("Show listings for women only.", "sex_or_gender"),
        ("Avoid homes near disabled residents.", "disability"),
    ],
)
def test_explicit_protected_class_requests_are_blocked(
    compliance_agent: ComplianceAgent,
    query: str,
    expected_category: str,
) -> None:
    report = compliance_agent.check_query(query)

    assert report.risk_level == "red"
    assert report.should_block is True
    assert expected_category in report.matched_categories
    assert report.refusal_message is not None


def test_accessibility_request_is_not_blocked(
    compliance_agent: ComplianceAgent,
) -> None:
    report = compliance_agent.check_query(
        "Find a wheelchair-accessible home near public transit."
    )

    assert report.risk_level == "green"
    assert report.should_block is False

def test_home_for_disabled_family_member_is_not_blocked(
    compliance_agent: ComplianceAgent,
) -> None:
    report = compliance_agent.check_query(
        "Find a home with accessible entrances for a disabled family member."
    )

    assert report.risk_level == "green"
    assert report.should_block is False