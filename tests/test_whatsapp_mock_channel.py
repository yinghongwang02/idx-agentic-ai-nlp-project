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
from src.orchestration.orchestrator import (
    Orchestrator,
)
from src.orchestration.router import (
    IntentRouter,
)


# =====================================================================
# Lightweight capability doubles
# =====================================================================


def fake_search_handler(state):
    return {
        "final_response": (
            "Found 3 homes matching the search criteria."
        ),
        "recommendations": [
            "listing-1",
            "listing-2",
            "listing-3",
        ],
        "blocked": False,
        "error": None,
    }


def fake_market_handler(state):
    return {
        "city": "Irvine",
        "summary": (
            "The Irvine market is currently stable."
        ),
    }


def fake_recommendation_handler(state):
    return []


def fake_knowledge_handler(state):
    return {
        "answer": (
            "DOM means Days on Market."
        ),
        "sources": [
            "mls_field_mapping.md",
        ],
    }


# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture
def runtime():
    router = IntentRouter()

    orchestrator = Orchestrator(
        router=router.route,
        search_handler=fake_search_handler,
        market_handler=fake_market_handler,
        recommendation_handler=(
            fake_recommendation_handler
        ),
        knowledge_handler=(
            fake_knowledge_handler
        ),
    )

    skill = RealEstateCopilotSkill(
        orchestrator=orchestrator,
    )

    return OpenClawRuntime(
        skill=skill,
    )


@pytest.fixture
def channel(tmp_path):
    return WhatsAppMockChannel(
        log_path=(
            tmp_path
            / "whatsapp_mock_log.json"
        )
    )


# =====================================================================
# Basic delivery
# =====================================================================


def test_whatsapp_mock_sends_message(
    channel,
):
    result = channel.send(
        OutboundMessage(
            recipient="+15550001111",
            text="Hello from the real-estate copilot.",
            session_id="session-123",
        )
    )

    assert result.success is True
    assert result.channel == "whatsapp_mock"
    assert result.recipient == (
        "+15550001111"
    )
    assert result.message_id is not None
    assert result.error is None


# =====================================================================
# Log persistence
# =====================================================================


def test_whatsapp_mock_writes_delivery_log(
    channel,
):
    channel.send(
        OutboundMessage(
            recipient="+15550002222",
            text="Your property results are ready.",
            session_id="session-log",
            metadata={
                "route": "search",
            },
        )
    )

    assert channel.log_path.exists()

    with channel.log_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        records = json.load(handle)

    assert len(records) == 1

    record = records[0]

    assert record["recipient"] == (
        "+15550002222"
    )
    assert record["session_id"] == (
        "session-log"
    )
    assert record["status"] == (
        "mock_delivered"
    )
    assert record["metadata"]["route"] == (
        "search"
    )


# =====================================================================
# Multiple deliveries append safely
# =====================================================================


def test_whatsapp_mock_appends_multiple_messages(
    channel,
):
    channel.send(
        OutboundMessage(
            recipient="+15550003333",
            text="First message.",
        )
    )

    channel.send(
        OutboundMessage(
            recipient="+15550003333",
            text="Second message.",
        )
    )

    with channel.log_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        records = json.load(handle)

    assert len(records) == 2

    assert records[0]["text"] == (
        "First message."
    )

    assert records[1]["text"] == (
        "Second message."
    )


# =====================================================================
# Validation
# =====================================================================


def test_whatsapp_mock_rejects_empty_text(
    channel,
):
    result = channel.send(
        OutboundMessage(
            recipient="+15550004444",
            text="   ",
        )
    )

    assert result.success is False

    assert result.error == (
        "Message text cannot be empty."
    )

    assert not channel.log_path.exists()


# =====================================================================
# Runtime -> WhatsApp integration
# =====================================================================


def test_runtime_response_can_be_sent_to_whatsapp(
    runtime,
    channel,
):
    runtime_response = (
        runtime.handle_message(
            (
                "Find homes in Irvine under "
                "$1.5M"
            ),
            session_id="buyer-456",
            channel="whatsapp",
        )
    )

    delivery = channel.send(
        OutboundMessage(
            recipient="+15550005555",
            text=runtime_response.text,
            session_id=(
                runtime_response.session_id
            ),
            metadata={
                "route": (
                    runtime_response.route
                ),
                "agents_invoked": list(
                    runtime_response
                    .agents_invoked
                ),
            },
        )
    )

    assert delivery.success is True

    with channel.log_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        records = json.load(handle)

    assert len(records) == 1

    record = records[0]

    assert (
        "Found 3 homes"
        in record["text"]
    )

    assert record["session_id"] == (
        "buyer-456"
    )

    assert record["metadata"]["route"] == (
        "search"
    )

    assert record["metadata"][
        "agents_invoked"
    ] == ["search"]