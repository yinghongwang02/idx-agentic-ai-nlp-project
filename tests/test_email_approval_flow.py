from __future__ import annotations

import pytest

from src.communication.email_approval import (
    EmailApprovalGate,
)
from src.communication.email_draft_agent import (
    EmailDraft,
    EmailDraftAgent,
)
from src.communication.mock_email_channel import (
    MockEmailChannel,
    SafeMockEmailSender,
)
from src.communication.outbound_safety import (
    OutboundSafetyGuard,
)
from src.orchestration.composition import (
    create_orchestrator,
)


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def real_orchestrator():
    return create_orchestrator()


@pytest.fixture
def email_agent():
    return EmailDraftAgent()


@pytest.fixture
def approval_gate():
    return EmailApprovalGate()


@pytest.fixture
def mock_channel():
    return MockEmailChannel()


@pytest.fixture
def safe_sender(
    mock_channel,
):
    return SafeMockEmailSender(
        channel=mock_channel,
        safety_guard=(
            OutboundSafetyGuard()
        ),
    )


def test_real_market_to_approved_mock_email(
    real_orchestrator,
    email_agent,
    approval_gate,
    safe_sender,
    mock_channel,
):
    # ---------------------------------------------------------
    # 1. Real LangGraph orchestration
    # ---------------------------------------------------------

    state = real_orchestrator.invoke(
        "Tell me about the Irvine real estate market."
    )

    assert state["route"] == "market"
    assert state.get(
        "market_result"
    ) is not None
    assert not state.get("errors")

    # ---------------------------------------------------------
    # 2. Real email draft
    # ---------------------------------------------------------

    draft = (
        email_agent
        .draft_weekly_market_report(
            to="buyer@example.com",
            market_summary=(
                state["market_result"]
            ),
        )
    )

    assert (
        draft.status
        == "pending_approval"
    )

    # ---------------------------------------------------------
    # 3. Explicit human approval
    # ---------------------------------------------------------

    approval = approval_gate.approve(
        draft,
        decided_by="integration-test-user",
    )

    assert approval.is_approved

    # ---------------------------------------------------------
    # 4. Safety → mock delivery
    # ---------------------------------------------------------

    delivery = (
        safe_sender.send_approved(
            approval,
            session_id=(
                "integration-market-001"
            ),
        )
    )

    assert delivery.success
    assert (
        delivery.channel
        == "mock_email"
    )

    assert (
        delivery.recipient
        == "buyer@example.com"
    )

    assert delivery.message_id

    # ---------------------------------------------------------
    # 5. Verify actual mock channel received it
    # ---------------------------------------------------------

    assert (
        len(mock_channel.sent_messages)
        == 1
    )

    sent = (
        mock_channel.sent_messages[0]
    )

    assert (
        sent.recipient
        == "buyer@example.com"
    )

    assert (
        "Market Summary"
        in sent.text
    )

    assert (
        sent.metadata[
            "approval_status"
        ]
        == "approved"
    )


def test_real_search_to_approved_mock_email(
    real_orchestrator,
    email_agent,
    approval_gate,
    safe_sender,
    mock_channel,
):
    # ---------------------------------------------------------
    # 1. Real LangGraph property search
    # ---------------------------------------------------------

    state = real_orchestrator.invoke(
        "Find homes in Irvine under $1.5M"
    )

    assert state["route"] == "search"
    assert state.get(
        "search_result"
    ) is not None
    assert not state.get("errors")

    search_result = state[
        "search_result"
    ]

    recommendations = (
        search_result.get(
            "recommendations",
            [],
        )
    )

    assert recommendations

    # ---------------------------------------------------------
    # 2. Draft from real recommendations
    # ---------------------------------------------------------

    draft = (
        email_agent
        .draft_property_digest(
            to="buyer@example.com",
            listings=recommendations,
            buyer_preferences=(
                "Homes in Irvine "
                "under $1.5M"
            ),
        )
    )

    assert (
        draft.metadata[
            "listing_count"
        ]
        > 0
    )

    # ---------------------------------------------------------
    # 3. Human approval
    # ---------------------------------------------------------

    approval = approval_gate.approve(
        draft,
        decided_by="integration-test-user",
    )

    # ---------------------------------------------------------
    # 4. Safety → mock delivery
    # ---------------------------------------------------------

    delivery = (
        safe_sender.send_approved(
            approval,
            session_id=(
                "integration-search-001"
            ),
        )
    )

    assert delivery.success

    assert (
        len(mock_channel.sent_messages)
        == 1
    )

    sent = (
        mock_channel.sent_messages[0]
    )

    assert (
        "Recommended Properties"
        in sent.text
    )

    assert (
        sent.metadata[
            "draft_type"
        ]
        == (
            "property_recommendation_digest"
        )
    )

    assert (
        sent.metadata[
            "approval_status"
        ]
        == "approved"
    )


def test_rejected_email_cannot_reach_channel(
    approval_gate,
    safe_sender,
    mock_channel,
):
    draft = EmailDraft(
        to="buyer@example.com",
        subject="Property Recommendations",
        body="Property recommendations.",
    )

    rejection = (
        approval_gate.reject(
            draft,
            decided_by="integration-test-user",
            reason="Not ready.",
        )
    )

    with pytest.raises(
        PermissionError,
        match="Outbound email blocked",
    ):
        safe_sender.send_approved(
            rejection
        )

    # Critical invariant:
    # blocked email never reaches the channel.
    assert (
        mock_channel.sent_messages
        == []
    )


def test_invalid_approved_email_cannot_reach_channel(
    approval_gate,
    safe_sender,
    mock_channel,
):
    draft = EmailDraft(
        to="invalid-recipient",
        subject="Market Report",
        body="Market report.",
    )

    approval = approval_gate.approve(
        draft,
        decided_by="integration-test-user",
    )

    with pytest.raises(
        PermissionError,
        match="Outbound email blocked",
    ):
        safe_sender.send_approved(
            approval
        )

    assert (
        mock_channel.sent_messages
        == []
    )


def test_mock_delivery_preserves_approval_metadata(
    approval_gate,
    safe_sender,
    mock_channel,
):
    draft = EmailDraft(
        to="buyer@example.com",
        subject="Market Report",
        body="Market report.",
        metadata={
            "draft_type": (
                "weekly_market_report"
            ),
            "city": "Irvine",
        },
    )

    approval = approval_gate.approve(
        draft,
        decided_by="streamlit-user",
    )

    delivery = (
        safe_sender.send_approved(
            approval,
            session_id="session-123",
        )
    )

    assert delivery.success

    sent = (
        mock_channel.sent_messages[0]
    )

    assert (
        sent.session_id
        == "session-123"
    )

    assert (
        sent.metadata[
            "draft_type"
        ]
        == "weekly_market_report"
    )

    assert (
        sent.metadata["city"]
        == "Irvine"
    )

    assert (
        sent.metadata[
            "approval_status"
        ]
        == "approved"
    )

    assert (
        sent.metadata[
            "approved_by"
        ]
        == "streamlit-user"
    )

    assert (
        sent.metadata[
            "subject"
        ]
        == "Market Report"
    )

    assert (
        sent.metadata[
            "approved_at"
        ]
    )