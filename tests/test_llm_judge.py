from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.evaluation.llm_judge import LLMJudge
from src.providers.base import BaseLLMProvider


class FakeLLMProvider(BaseLLMProvider):
    def __init__(self, response: str) -> None:
        self.response = response
        self.system_prompt: str | None = None
        self.user_prompt: str | None = None

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return self.response


def test_evaluate_parses_valid_judge_result() -> None:
    provider = FakeLLMProvider(
        """
        {
          "correctness": 5,
          "relevance": 4,
          "groundedness": 5,
          "rationale": "The response matches the supplied evidence."
        }
        """
    )

    judge = LLMJudge(provider)

    result = judge.evaluate(
        user_query="Tell me about the Irvine market.",
        response="Median close price is $1.54M.",
        evidence={
            "city": "Irvine",
            "median_close_price": 1540000,
        },
    )

    assert result.correctness == 5
    assert result.relevance == 4
    assert result.groundedness == 5
    assert (
        result.rationale
        == "The response matches the supplied evidence."
    )


def test_evaluate_passes_query_response_and_evidence_to_provider() -> None:
    provider = FakeLLMProvider(
        """
        {
          "correctness": 5,
          "relevance": 5,
          "groundedness": 5,
          "rationale": "Supported."
        }
        """
    )

    judge = LLMJudge(provider)

    judge.evaluate(
        user_query="What does DOM mean?",
        response="DOM means days on market.",
        evidence={
            "source": "real_estate_terminology.md",
            "content": "DOM means days on market.",
        },
    )

    assert provider.system_prompt is not None
    assert provider.user_prompt is not None

    assert "What does DOM mean?" in provider.user_prompt
    assert "DOM means days on market." in provider.user_prompt
    assert "real_estate_terminology.md" in provider.user_prompt


def test_evaluate_accepts_fenced_json() -> None:
    provider = FakeLLMProvider(
        """```json
{
  "correctness": 4,
  "relevance": 5,
  "groundedness": 4,
  "rationale": "Mostly supported."
}
```"""
    )

    judge = LLMJudge(provider)

    result = judge.evaluate(
        user_query="Test query",
        response="Test response",
        evidence={"value": 123},
    )

    assert result.correctness == 4
    assert result.relevance == 5
    assert result.groundedness == 4


def test_evaluate_rejects_invalid_json() -> None:
    provider = FakeLLMProvider(
        "This is not JSON."
    )

    judge = LLMJudge(provider)

    with pytest.raises(
        ValueError,
        match="invalid JSON",
    ):
        judge.evaluate(
            user_query="Test query",
            response="Test response",
            evidence={},
        )


def test_evaluate_rejects_score_above_five() -> None:
    provider = FakeLLMProvider(
        """
        {
          "correctness": 6,
          "relevance": 5,
          "groundedness": 5,
          "rationale": "Invalid score."
        }
        """
    )

    judge = LLMJudge(provider)

    with pytest.raises(ValidationError):
        judge.evaluate(
            user_query="Test query",
            response="Test response",
            evidence={},
        )


def test_evaluate_rejects_score_below_one() -> None:
    provider = FakeLLMProvider(
        """
        {
          "correctness": 0,
          "relevance": 5,
          "groundedness": 5,
          "rationale": "Invalid score."
        }
        """
    )

    judge = LLMJudge(provider)

    with pytest.raises(ValidationError):
        judge.evaluate(
            user_query="Test query",
            response="Test response",
            evidence={},
        )


def test_evaluate_rejects_empty_query() -> None:
    provider = FakeLLMProvider(
        """
        {
          "correctness": 5,
          "relevance": 5,
          "groundedness": 5,
          "rationale": "Supported."
        }
        """
    )

    judge = LLMJudge(provider)

    with pytest.raises(
        ValueError,
        match="user_query must not be empty",
    ):
        judge.evaluate(
            user_query="   ",
            response="Test response",
            evidence={},
        )


def test_evaluate_rejects_empty_response() -> None:
    provider = FakeLLMProvider(
        """
        {
          "correctness": 5,
          "relevance": 5,
          "groundedness": 5,
          "rationale": "Supported."
        }
        """
    )

    judge = LLMJudge(provider)

    with pytest.raises(
        ValueError,
        match="response must not be empty",
    ):
        judge.evaluate(
            user_query="Test query",
            response="   ",
            evidence={},
        )