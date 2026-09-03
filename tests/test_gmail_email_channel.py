

import base64
from email import policy
from email.parser import BytesParser

import pytest

from src.communication.base_channel import OutboundMessage
from src.communication.email_approval import EmailApprovalGate
from src.communication.email_draft_agent import EmailDraft
from src.communication.gmail_email_channel import (
    GmailEmailChannel,
    SafeGmailEmailSender,
)


class FakeGmailSendRequest:
    def __init__(
        self,
        *,
        response: dict | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response or {
            "id": "gmail-message-123"
        }
        self.error = error

    def execute(self) -> dict:
        if self.error is not None:
            raise self.error

        return self.response


class FakeGmailMessages:
    def __init__(
        self,
        *,
        response: dict | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.send_calls: list[dict] = []

    def send(
        self,
        *,
        userId: str,
        body: dict,
    ) -> FakeGmailSendRequest:
        self.send_calls.append(
            {
                "userId": userId,
                "body": body,
            }
        )

        return FakeGmailSendRequest(
            response=self.response,
            error=self.error,
        )


class FakeGmailUsers:
    def __init__(
        self,
        messages: FakeGmailMessages,
    ) -> None:
        self._messages = messages

    def messages(self) -> FakeGmailMessages:
        return self._messages


class FakeGmailService:
    def __init__(
        self,
        *,
        response: dict | None = None,
        error: Exception | None = None,
    ) -> None:
        self.messages_api = FakeGmailMessages(
            response=response,
            error=error,
        )
        self._users = FakeGmailUsers(
            self.messages_api
        )

    def users(self) -> FakeGmailUsers:
        return self._users


def decode_raw_message(
    raw_message: str,
):
    padded = raw_message + (
        "=" * (-len(raw_message) % 4)
    )

    message_bytes = base64.urlsafe_b64decode(
        padded.encode("utf-8")
    )

    return BytesParser(
        policy=policy.default
    ).parsebytes(
        message_bytes
    )


def make_draft(
    *,
    to: str = "buyer@example.com",
    subject: str = "Irvine Property Recommendations",
    body: str = "Here are your recommended properties.",
) -> EmailDraft:
    return EmailDraft(
        to=to,
        subject=subject,
        body=body,
        metadata={
            "draft_type": (
                "property_recommendation_digest"
            ),
            "city": "Irvine",
        },
    )


def test_gmail_channel_sends_expected_payload() -> None:
    service = FakeGmailService()

    channel = GmailEmailChannel(
        service=service
    )

    message = OutboundMessage(
        recipient="buyer@example.com",
        text="Hello from the IDX copilot.",
        session_id="session-123",
        metadata={
            "subject": "Irvine Homes",
        },
    )

    result = channel.send(
        message
    )

    assert result.success is True
    assert result.channel == "gmail"
    assert result.recipient == (
        "buyer@example.com"
    )
    assert result.message_id == (
        "gmail-message-123"
    )
    assert result.error is None

    assert len(
        service.messages_api.send_calls
    ) == 1

    call = (
        service.messages_api.send_calls[0]
    )

    assert call["userId"] == "me"
    assert "raw" in call["body"]


def test_gmail_channel_encodes_recipient_subject_and_body() -> None:
    service = FakeGmailService()

    channel = GmailEmailChannel(
        service=service
    )

    channel.send(
        OutboundMessage(
            recipient="buyer@example.com",
            text=(
                "Property 1\n"
                "Property 2"
            ),
            metadata={
                "subject": (
                    "Property Recommendations "
                    "in Irvine"
                ),
            },
        )
    )

    raw_message = (
        service.messages_api
        .send_calls[0]["body"]["raw"]
    )

    parsed = decode_raw_message(
        raw_message
    )

    assert parsed["To"] == (
        "buyer@example.com"
    )
    assert parsed["Subject"] == (
        "Property Recommendations in Irvine"
    )

    body = parsed.get_content()

    assert "Property 1" in body
    assert "Property 2" in body


def test_gmail_channel_preserves_provider_message_id() -> None:
    service = FakeGmailService(
        response={
            "id": "realistic-gmail-id-456",
            "threadId": "thread-789",
        }
    )

    channel = GmailEmailChannel(
        service=service
    )

    result = channel.send(
        OutboundMessage(
            recipient="buyer@example.com",
            text="Test body",
            metadata={
                "subject": "Test subject",
            },
        )
    )

    assert result.success is True
    assert result.message_id == (
        "realistic-gmail-id-456"
    )


def test_gmail_channel_blocks_missing_subject_before_api_call() -> None:
    service = FakeGmailService()

    channel = GmailEmailChannel(
        service=service
    )

    result = channel.send(
        OutboundMessage(
            recipient="buyer@example.com",
            text="Test body",
            metadata={},
        )
    )

    assert result.success is False
    assert result.channel == "gmail"
    assert result.message_id is None
    assert (
        "requires metadata['subject']"
        in (result.error or "")
    )

    assert (
        service.messages_api.send_calls
        == []
    )


def test_gmail_channel_blocks_subject_header_injection() -> None:
    service = FakeGmailService()

    channel = GmailEmailChannel(
        service=service
    )

    result = channel.send(
        OutboundMessage(
            recipient="buyer@example.com",
            text="Test body",
            metadata={
                "subject": (
                    "Safe subject\r\n"
                    "Bcc: attacker@example.com"
                ),
            },
        )
    )

    assert result.success is False
    assert (
        "newline characters"
        in (result.error or "")
    )

    assert (
        service.messages_api.send_calls
        == []
    )


def test_gmail_channel_returns_failed_delivery_on_api_error() -> None:
    service = FakeGmailService(
        error=RuntimeError(
            "simulated Gmail API failure"
        )
    )

    channel = GmailEmailChannel(
        service=service
    )

    result = channel.send(
        OutboundMessage(
            recipient="buyer@example.com",
            text="Test body",
            metadata={
                "subject": "Test subject",
            },
        )
    )

    assert result.success is False
    assert result.channel == "gmail"
    assert result.recipient == (
        "buyer@example.com"
    )
    assert result.message_id is None
    assert (
        "simulated Gmail API failure"
        in (result.error or "")
    )

    assert len(
        service.messages_api.send_calls
    ) == 1


def test_safe_gmail_sender_sends_only_after_explicit_approval() -> None:
    service = FakeGmailService()

    channel = GmailEmailChannel(
        service=service
    )

    sender = SafeGmailEmailSender(
        channel=channel
    )

    draft = make_draft()

    approval = EmailApprovalGate().approve(
        draft,
        decided_by="unit-test-reviewer",
    )

    result = sender.send_approved(
        approval,
        session_id="session-approved",
    )

    assert result.success is True

    assert len(
        service.messages_api.send_calls
    ) == 1

    raw_message = (
        service.messages_api
        .send_calls[0]["body"]["raw"]
    )

    parsed = decode_raw_message(
        raw_message
    )

    assert parsed["To"] == draft.to
    assert parsed["Subject"] == (
        draft.subject
    )
    assert draft.body in (
        parsed.get_content()
    )


def test_safe_gmail_sender_rejects_unapproved_email_without_api_call() -> None:
    service = FakeGmailService()

    channel = GmailEmailChannel(
        service=service
    )

    sender = SafeGmailEmailSender(
        channel=channel
    )

    draft = make_draft()

    rejection = EmailApprovalGate().reject(
        draft,
        decided_by="unit-test-reviewer",
        reason="Not approved for delivery.",
    )

    with pytest.raises(
        PermissionError
    ):
        sender.send_approved(
            rejection
        )

    assert (
        service.messages_api.send_calls
        == []
    )
