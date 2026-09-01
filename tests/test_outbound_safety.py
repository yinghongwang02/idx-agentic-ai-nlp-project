from __future__ import annotations

import pytest

from src.communication.email_approval import (
    EmailApprovalGate,
    EmailApprovalRecord,
)
from src.communication.email_draft_agent import (
    EmailDraft,
)
from src.communication.outbound_safety import (
    OutboundSafetyGuard,
)


@pytest.fixture
def gate():
    return EmailApprovalGate()


@pytest.fixture
def guard():
    return OutboundSafetyGuard()


@pytest.fixture
def draft():
    return EmailDraft(
        to="buyer@example.com",
        subject="Weekly Real Estate Market Report — Irvine",
        body=(
            "Hello,\n\n"
            "Here is your weekly Irvine market report."
        ),
    )


def test_approved_email_passes_outbound_safety(
    gate,
    guard,
    draft,
):
    approval = gate.approve(
        draft,
        decided_by="streamlit-user",
    )

    result = guard.check(
        approval
    )

    assert result.allowed
    assert result.reasons == ()


def test_rejected_email_is_blocked(
    gate,
    guard,
    draft,
):
    approval = gate.reject(
        draft,
        decided_by="streamlit-user",
        reason="Not ready to send.",
    )

    result = guard.check(
        approval
    )

    assert not result.allowed

    assert (
        "Email has not been explicitly approved."
        in result.reasons
    )


def test_missing_approval_record_is_blocked(
    guard,
):
    result = guard.check(
        None  # type: ignore[arg-type]
    )

    assert not result.allowed

    assert result.reasons == (
        "Missing valid email approval record.",
    )


def test_invalid_recipient_is_blocked(
    gate,
    guard,
):
    draft = EmailDraft(
        to="not-an-email",
        subject="Market Report",
        body="Market report content.",
    )

    approval = gate.approve(
        draft,
        decided_by="streamlit-user",
    )

    result = guard.check(
        approval
    )

    assert not result.allowed

    assert (
        "Email recipient is invalid."
        in result.reasons
    )


def test_multiple_recipients_are_blocked(
    gate,
    guard,
):
    draft = EmailDraft(
        to=(
            "buyer1@example.com,"
            "buyer2@example.com"
        ),
        subject="Market Report",
        body="Market report content.",
    )

    approval = gate.approve(
        draft,
        decided_by="streamlit-user",
    )

    result = guard.check(
        approval
    )

    assert not result.allowed

    assert (
        "Multiple recipients are not allowed "
        "by the current outbound safety policy."
        in result.reasons
    )


def test_empty_subject_is_blocked(
    gate,
    guard,
):
    draft = EmailDraft(
        to="buyer@example.com",
        subject="   ",
        body="Market report content.",
    )

    approval = gate.approve(
        draft,
        decided_by="streamlit-user",
    )

    result = guard.check(
        approval
    )

    assert not result.allowed

    assert (
        "Email subject is empty."
        in result.reasons
    )


def test_empty_body_is_blocked(
    gate,
    guard,
):
    draft = EmailDraft(
        to="buyer@example.com",
        subject="Market Report",
        body="   ",
    )

    approval = gate.approve(
        draft,
        decided_by="streamlit-user",
    )

    result = guard.check(
        approval
    )

    assert not result.allowed

    assert (
        "Email body is empty."
        in result.reasons
    )


def test_require_safe_allows_approved_email(
    gate,
    guard,
    draft,
):
    approval = gate.approve(
        draft,
        decided_by="streamlit-user",
    )

    guard.require_safe(
        approval
    )


def test_require_safe_raises_for_rejected_email(
    gate,
    guard,
    draft,
):
    approval = gate.reject(
        draft,
        decided_by="streamlit-user",
    )

    with pytest.raises(
        PermissionError,
        match="Outbound email blocked",
    ):
        guard.require_safe(
            approval
        )