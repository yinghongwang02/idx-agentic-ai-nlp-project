from __future__ import annotations

from uuid import uuid4

from src.communication.base_channel import (
    DeliveryResult,
    OutboundMessage,
)
from src.communication.email_approval import (
    EmailApprovalRecord,
)
from src.communication.outbound_safety import (
    OutboundSafetyGuard,
)


class MockEmailChannel:
    """
    In-memory email delivery channel for development and tests.

    This channel never contacts a real email provider.
    It records messages that would have been sent.
    """

    name = "mock_email"

    def __init__(self) -> None:
        self.sent_messages: list[
            OutboundMessage
        ] = []

    def send(
        self,
        message: OutboundMessage,
    ) -> DeliveryResult:
        self.sent_messages.append(
            message
        )

        return DeliveryResult(
            success=True,
            channel=self.name,
            recipient=message.recipient,
            message_id=(
                f"mock-{uuid4().hex}"
            ),
        )


class SafeMockEmailSender:
    """
    Approval-enforcing boundary around MockEmailChannel.

    Callers cannot send an EmailDraft directly. They must provide
    an EmailApprovalRecord, and the outbound safety guard must pass
    before the message reaches the channel.

    The same pattern can later wrap a real Gmail channel.
    """

    def __init__(
        self,
        *,
        channel: MockEmailChannel | None = None,
        safety_guard: OutboundSafetyGuard | None = None,
    ) -> None:
        self.channel = (
            channel
            or MockEmailChannel()
        )

        self.safety_guard = (
            safety_guard
            or OutboundSafetyGuard()
        )

    def send_approved(
        self,
        approval: EmailApprovalRecord,
        *,
        session_id: str | None = None,
    ) -> DeliveryResult:
        # Critical safety boundary:
        # delivery cannot happen before this passes.
        self.safety_guard.require_safe(
            approval
        )

        draft = approval.draft

        message = OutboundMessage(
            recipient=draft.to,
            text=draft.body,
            session_id=session_id,
            metadata={
                **draft.metadata,
                "subject": draft.subject,
                "approval_status": (
                    approval.status
                ),
                "approved_by": (
                    approval.decided_by
                ),
                "approved_at": (
                    approval.decided_at.isoformat()
                ),
            },
        )

        return self.channel.send(
            message
        )