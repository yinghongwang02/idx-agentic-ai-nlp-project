from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from src.providers.base import BaseLLMProvider


class JudgeResult(BaseModel):
    correctness: int = Field(ge=1, le=5)
    relevance: int = Field(ge=1, le=5)
    groundedness: int = Field(ge=1, le=5)
    rationale: str


class LLMJudge:
    """
    Offline semantic evaluator for Unified Copilot responses.

    The judge does not participate in production routing or generation.
    It evaluates an already-completed response against the user request
    and structured evidence produced by the application.
    """

    SYSTEM_PROMPT = """
You are an evaluator for a real-estate multi-agent system.

Evaluate the assistant response using only:
1. the user request;
2. the application evidence supplied below; and
3. the assistant response.

Score each dimension from 1 to 5.

Correctness:
5 = response accurately reflects the supplied evidence.
1 = response substantially contradicts or misrepresents the evidence.

Relevance:
5 = response directly and usefully addresses the user request.
1 = response is largely irrelevant to the request.

Groundedness:
5 = factual claims are clearly supported by the supplied application evidence.
1 = factual claims are unsupported or contradict the supplied evidence.

Do not use outside real-estate knowledge to verify market facts, prices,
listings, or retrieved knowledge. Judge grounding against the supplied
application evidence.

Return JSON only, using exactly this schema:

{
  "correctness": 1,
  "relevance": 1,
  "groundedness": 1,
  "rationale": "brief explanation"
}
""".strip()

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
    ) -> None:
        self.llm_provider = llm_provider

    def evaluate(
        self,
        *,
        user_query: str,
        response: str,
        evidence: Any,
    ) -> JudgeResult:
        if not user_query.strip():
            raise ValueError("user_query must not be empty")

        if not response.strip():
            raise ValueError("response must not be empty")

        evidence_text = self._serialize_evidence(
            evidence
        )

        user_prompt = (
            f"USER REQUEST:\n{user_query}\n\n"
            f"APPLICATION EVIDENCE:\n{evidence_text}\n\n"
            f"ASSISTANT RESPONSE:\n{response}"
        )

        raw_result = self.llm_provider.generate(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        payload = self._parse_json(raw_result)

        return JudgeResult.model_validate(payload)

    @staticmethod
    def _serialize_evidence(
        evidence: Any,
    ) -> str:
        try:
            return json.dumps(
                evidence,
                default=str,
                ensure_ascii=False,
                indent=2,
            )
        except (TypeError, ValueError):
            return str(evidence)

    @staticmethod
    def _parse_json(raw_result: str) -> dict[str, Any]:
        text = raw_result.strip()

        if text.startswith("```"):
            lines = text.splitlines()

            if lines:
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            text = "\n".join(lines).strip()

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "LLM judge returned invalid JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise ValueError(
                "LLM judge response must be a JSON object."
            )

        return payload