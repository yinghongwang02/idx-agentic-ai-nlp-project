from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["green", "yellow", "red"]
CheckTarget = Literal["query", "output"]


class ComplianceMatch(BaseModel):
    """
    One compliance rule matched in a query or generated output.
    """

    category: str
    matched_text: str
    reason: str
    risk_level: RiskLevel


class ComplianceReport(BaseModel):
    """
    Structured result returned by the ComplianceAgent.
    """

    target: CheckTarget
    original_text: str

    risk_level: RiskLevel = "green"
    is_compliant: bool = True
    should_block: bool = False

    matched_categories: list[str] = Field(default_factory=list)
    matches: list[ComplianceMatch] = Field(default_factory=list)

    safe_rewrite: str | None = None
    refusal_message: str | None = None

    rule_version: str = "fair-housing-rules-v1"