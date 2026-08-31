from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.communication.base_channel import (
    DeliveryResult,
    OutboundMessage,
)


DEFAULT_LOG_PATH = Path(
    "logs/whatsapp_mock_log.json"
)


class WhatsAppMockChannel:
    """
    Mock WhatsApp outbound channel.

    The channel does not call a real WhatsApp provider.
    Instead, it records outbound deliveries to a local JSON log so the
    communication workflow can be demonstrated and tested safely.
    """

    name = "whatsapp_mock"

    def __init__(
        self,
        *,
        log_path: Path = DEFAULT_LOG_PATH,
    ) -> None:
        self.log_path = log_path

    def send(
        self,
        message: OutboundMessage,
    ) -> DeliveryResult:
        recipient = str(
            message.recipient or ""
        ).strip()

        text = str(
            message.text or ""
        ).strip()

        if not recipient:
            return DeliveryResult(
                success=False,
                channel=self.name,
                recipient="",
                error="Recipient cannot be empty.",
            )

        if not text:
            return DeliveryResult(
                success=False,
                channel=self.name,
                recipient=recipient,
                error="Message text cannot be empty.",
            )

        message_id = (
            f"wa-mock-{uuid4().hex[:12]}"
        )

        record = {
            "message_id": message_id,
            "channel": self.name,
            "recipient": recipient,
            "text": text,
            "session_id": message.session_id,
            "metadata": (
                message.metadata or {}
            ),
            "sent_at": (
                datetime.now(timezone.utc)
                .isoformat()
            ),
            "status": "mock_delivered",
        }

        try:
            self._append_log(record)

        except Exception as exc:
            return DeliveryResult(
                success=False,
                channel=self.name,
                recipient=recipient,
                message_id=message_id,
                error=(
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )

        return DeliveryResult(
            success=True,
            channel=self.name,
            recipient=recipient,
            message_id=message_id,
        )

    def _append_log(
        self,
        record: dict,
    ) -> None:
        self.log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        records = self._load_existing_records()

        records.append(record)

        with self.log_path.open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                records,
                handle,
                indent=2,
                ensure_ascii=False,
            )

    def _load_existing_records(
        self,
    ) -> list[dict]:
        if not self.log_path.exists():
            return []

        try:
            with self.log_path.open(
                "r",
                encoding="utf-8",
            ) as handle:
                data = json.load(handle)

        except json.JSONDecodeError:
            return []

        if not isinstance(data, list):
            return []

        return data