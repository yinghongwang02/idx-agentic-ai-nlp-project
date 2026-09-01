from __future__ import annotations

from datetime import timezone

import pytest

from src.communication.email_approval import (
    EmailApprovalGate,
)
from src.communication.email_draft_agent import (
    EmailDraft,
)


@pytest.fixture
def gate():
    return EmailApprovalGate()


@pytest.fixture
def draft():
    return EmailDraft(
        to="buyer@example.com",
        subject="Property Recommendations in Irvine",
        body=(
            "Hello,\n\n"
            "Here are your recommended properties."
        ),
    )


def test_approve_creates_explicit_approval_record(
    gate,
    draft,
):
    approval = gate.approve(
        draft,
        decided_by="streamlit-user",
    )

    assert approval.status == "approved"
    assert approval.is_approved
    assert not approval.is_rejected

    assert approval.draft is draft

    assert (
        approval.decided_by
        == "streamlit-user"
    )

    assert (
        approval.decided_at.tzinfo
        is not None
    )

    assert (
        approval.decided_at.utcoffset()
        == timezone.utc.utcoffset(
            approval.decided_at
        )
    )


def test_reject_creates_rejection_record(
    gate,
    draft,
):
    approval = gate.reject(
        draft,
        decided_by="streamlit-user",
        reason="Recipient needs review.",
    )

    assert approval.status == "rejected"
    assert approval.is_rejected
    assert not approval.is_approved

    assert approval.reason == (
        "Recipient needs review."
    )


def test_draft_remains_pending_after_approval(
    gate,
    draft,
):
    approval = gate.approve(
        draft,
        decided_by="streamlit-user",
    )

    assert (
        draft.status
        == "pending_approval"
    )

    assert (
        approval.draft.status
        == "pending_approval"
    )

    assert (
        approval.status
        == "approved"
    )


def test_approve_requires_explicit_human_actor(
    gate,
    draft,
):
    with pytest.raises(
        ValueError,
        match="explicit human actor",
    ):
        gate.approve(
            draft,
            decided_by="   ",
        )


def test_reject_requires_explicit_human_actor(
    gate,
    draft,
):
    with pytest.raises(
        ValueError,
        match="explicit human actor",
    ):
        gate.reject(
            draft,
            decided_by="",
        )


def test_approval_gate_rejects_non_email_draft(
    gate,
):
    with pytest.raises(
        TypeError,
        match="requires an EmailDraft",
    ):
        gate.approve(
            "not-a-draft",  # type: ignore[arg-type]
            decided_by="streamlit-user",
        )