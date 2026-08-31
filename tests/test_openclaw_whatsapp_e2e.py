from __future__ import annotations

import json

import pytest

from src.communication.base_channel import (
    OutboundMessage,
)
from src.communication.whatsapp_mock import (
    WhatsAppMockChannel,
)
from src.openclaw_runtime.runtime import (
    OpenClawRuntime,
)
from src.openclaw_runtime.skill_adapter import (
    RealEstateCopilotSkill,
)
from src.orchestration.composition import (
    create_orchestrator,
)


pytestmark = pytest.mark.integration


# =====================================================================
# Real application runtime
# =====================================================================


@pytest.fixture(scope="module")
def real_runtime():
    """
    Build the real application stack once for this integration module.

    This uses:
    - real composition root
    - real LangGraph orchestrator
    - real router
    - real MySQL repositories
    - real knowledge RAG
    - real providers/artifacts

    Only the final WhatsApp delivery remains mocked.
    """

    orchestrator = create_orchestrator()

    skill = RealEstateCopilotSkill(
        orchestrator=orchestrator,
    )

    return OpenClawRuntime(
        skill=skill,
    )


@pytest.fixture
def whatsapp_channel(tmp_path):
    """
    Use an isolated temporary WhatsApp log for every test.
    """

    return WhatsAppMockChannel(
        log_path=(
            tmp_path
            / "whatsapp_e2e_log.json"
        )
    )


# =====================================================================
# Helper
# =====================================================================


def send_runtime_response_to_whatsapp(
    *,
    runtime_response,
    channel,
    recipient: str,
):
    """
    Bridge a real runtime response into the outbound WhatsApp mock.
    """

    return channel.send(
        OutboundMessage(
            recipient=recipient,
            text=runtime_response.text,
            session_id=(
                runtime_response.session_id
            ),
            metadata={
                "route": (
                    runtime_response.route
                ),
                "routes": list(
                    runtime_response.routes
                ),
                "agents_invoked": list(
                    runtime_response.agents_invoked
                ),
            },
        )
    )


def load_single_delivery(channel):
    """
    Load and return the single WhatsApp mock delivery record.
    """

    assert channel.log_path.exists()

    with channel.log_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        records = json.load(handle)

    assert len(records) == 1

    return records[0]


# =====================================================================
# Search E2E
# =====================================================================


def test_real_search_request_reaches_whatsapp(
    real_runtime,
    whatsapp_channel,
):
    runtime_response = (
        real_runtime.handle_message(
            "Find homes in Irvine under $1.5M",
            session_id="e2e-search",
            channel="whatsapp",
        )
    )

    assert runtime_response.route == "search"

    assert runtime_response.routes == (
        "search",
    )

    assert "search" in (
        runtime_response.agents_invoked
    )

    assert runtime_response.text.strip()

    assert (
        runtime_response.raw_state.get(
            "search_result"
        )
        is not None
    )

    assert not runtime_response.errors

    delivery = (
        send_runtime_response_to_whatsapp(
            runtime_response=runtime_response,
            channel=whatsapp_channel,
            recipient="+15550001001",
        )
    )

    assert delivery.success is True

    record = load_single_delivery(
        whatsapp_channel
    )

    assert record["status"] == (
        "mock_delivered"
    )

    assert record["session_id"] == (
        "e2e-search"
    )

    assert record["metadata"]["route"] == (
        "search"
    )

    assert record["text"] == (
        runtime_response.text
    )


# =====================================================================
# Knowledge E2E
# =====================================================================


def test_real_knowledge_request_reaches_whatsapp(
    real_runtime,
    whatsapp_channel,
):
    runtime_response = (
        real_runtime.handle_message(
            (
                "What does DOM mean "
                "in real estate?"
            ),
            session_id="e2e-knowledge",
            channel="whatsapp",
        )
    )

    assert (
        runtime_response.route
        == "knowledge"
    )

    assert runtime_response.routes == (
        "knowledge",
    )

    assert "knowledge" in (
        runtime_response.agents_invoked
    )

    assert runtime_response.text.strip()

    assert (
        runtime_response.raw_state.get(
            "knowledge_result"
        )
        is not None
    )

    assert not runtime_response.errors

    delivery = (
        send_runtime_response_to_whatsapp(
            runtime_response=runtime_response,
            channel=whatsapp_channel,
            recipient="+15550001002",
        )
    )

    assert delivery.success is True

    record = load_single_delivery(
        whatsapp_channel
    )

    assert record["session_id"] == (
        "e2e-knowledge"
    )

    assert record["metadata"]["route"] == (
        "knowledge"
    )

    assert record["text"] == (
        runtime_response.text
    )


# =====================================================================
# Mixed Search + Market E2E
# =====================================================================


def test_real_mixed_request_reaches_whatsapp(
    real_runtime,
    whatsapp_channel,
):
    runtime_response = (
        real_runtime.handle_message(
            (
                "Find homes in Irvine under "
                "$1.5M and tell me about "
                "the local market."
            ),
            session_id="e2e-mixed",
            channel="whatsapp",
        )
    )

    assert runtime_response.route == "mixed"

    assert set(
        runtime_response.routes
    ) == {
        "search",
        "market",
    }

    assert set(
        runtime_response.agents_invoked
    ) == {
        "search",
        "market",
    }

    assert runtime_response.text.strip()

    assert (
        "Property Search:"
        in runtime_response.text
    )

    assert (
        "Market Analysis:"
        in runtime_response.text
    )

    state = runtime_response.raw_state

    assert (
        state.get("search_result")
        is not None
    )

    assert (
        state.get("market_result")
        is not None
    )

    assert not runtime_response.errors

    delivery = (
        send_runtime_response_to_whatsapp(
            runtime_response=runtime_response,
            channel=whatsapp_channel,
            recipient="+15550001003",
        )
    )

    assert delivery.success is True

    record = load_single_delivery(
        whatsapp_channel
    )

    assert record["session_id"] == (
        "e2e-mixed"
    )

    assert record["metadata"]["route"] == (
        "mixed"
    )

    assert set(
        record["metadata"]["routes"]
    ) == {
        "search",
        "market",
    }

    assert record["text"] == (
        runtime_response.text
    )