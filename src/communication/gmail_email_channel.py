from __future__ import annotations

import base64
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.communication.base_channel import CommunicationChannel, DeliveryResult, OutboundMessage
from src.communication.email_approval import EmailApprovalRecord
from src.communication.outbound_safety import OutboundSafetyGuard


GMAIL_SEND_SCOPES = ("https://www.googleapis.com/auth/gmail.send",)
DEFAULT_GMAIL_CREDENTIALS_PATH = Path("secrets/gmail_credentials.json")
DEFAULT_GMAIL_TOKEN_PATH = Path("secrets/gmail_token.json")


def load_gmail_credentials(
    *,
    credentials_path: Path = DEFAULT_GMAIL_CREDENTIALS_PATH,
    token_path: Path = DEFAULT_GMAIL_TOKEN_PATH,
    scopes: tuple[str, ...] = GMAIL_SEND_SCOPES,
) -> Credentials:
    credentials_path = Path(credentials_path)
    token_path = Path(token_path)
    credentials: Credentials | None = None

    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(
            str(token_path),
            list(scopes),
        )

    if credentials is not None and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if credentials is None or not credentials.valid:
        if not credentials_path.exists():
            raise FileNotFoundError(
                f"Gmail OAuth client credentials file was not found: {credentials_path}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path),
            scopes=list(scopes),
        )
        credentials = flow.run_local_server(port=0, open_browser=True)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    return credentials


def build_gmail_service(
    *,
    credentials_path: Path = DEFAULT_GMAIL_CREDENTIALS_PATH,
    token_path: Path = DEFAULT_GMAIL_TOKEN_PATH,
) -> Any:
    credentials = load_gmail_credentials(
        credentials_path=credentials_path,
        token_path=token_path,
    )

    return build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )


class GmailEmailChannel:
    name = "gmail"

    def __init__(
        self,
        *,
        credentials_path: Path = DEFAULT_GMAIL_CREDENTIALS_PATH,
        token_path: Path = DEFAULT_GMAIL_TOKEN_PATH,
        service: Any | None = None,
    ) -> None:
        self._credentials_path = Path(credentials_path)
        self._token_path = Path(token_path)
        self._service = service

    def send(self, message: OutboundMessage) -> DeliveryResult:
        try:
            subject = self._resolve_subject(message)

            gmail_message = EmailMessage()
            gmail_message["To"] = message.recipient
            gmail_message["Subject"] = subject
            gmail_message.set_content(message.text)

            raw_message = base64.urlsafe_b64encode(
                gmail_message.as_bytes()
            ).decode("utf-8")

            response = (
                self._get_service()
                .users()
                .messages()
                .send(
                    userId="me",
                    body={"raw": raw_message},
                )
                .execute()
            )

            return DeliveryResult(
                success=True,
                channel=self.name,
                recipient=message.recipient,
                message_id=response.get("id"),
            )

        except Exception as exc:
            return DeliveryResult(
                success=False,
                channel=self.name,
                recipient=message.recipient,
                error=str(exc),
            )

    def _get_service(self) -> Any:
        if self._service is None:
            self._service = build_gmail_service(
                credentials_path=self._credentials_path,
                token_path=self._token_path,
            )
        return self._service

    @staticmethod
    def _resolve_subject(message: OutboundMessage) -> str:
        metadata = message.metadata or {}
        subject = str(metadata.get("subject") or "").strip()

        if not subject:
            raise ValueError(
                "Outbound Gmail message requires metadata['subject']."
            )

        if "\r" in subject or "\n" in subject:
            raise ValueError(
                "Email subject cannot contain newline characters."
            )

        return subject


class SafeGmailEmailSender:
    def __init__(
        self,
        *,
        channel: CommunicationChannel | None = None,
        safety_guard: OutboundSafetyGuard | None = None,
    ) -> None:
        self.channel = channel or GmailEmailChannel()
        self.safety_guard = safety_guard or OutboundSafetyGuard()

    def send_approved(
        self,
        approval: EmailApprovalRecord,
        *,
        session_id: str | None = None,
    ) -> DeliveryResult:
        self.safety_guard.require_safe(approval)
        draft = approval.draft

        message = OutboundMessage(
            recipient=draft.to,
            text=draft.body,
            session_id=session_id,
            metadata={
                **draft.metadata,
                "subject": draft.subject,
                "approval_status": approval.status,
                "approved_by": approval.decided_by,
                "approved_at": approval.decided_at.isoformat(),
            },
        )

        return self.channel.send(message)