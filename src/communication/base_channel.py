from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OutboundMessage:
    """
    Normalized outbound message passed to a communication channel.
    """

    recipient: str
    text: str
    session_id: str | None = None
    metadata: dict | None = None


@dataclass(frozen=True)
class DeliveryResult:
    """
    Normalized delivery result returned by communication channels.
    """

    success: bool
    channel: str
    recipient: str
    message_id: str | None = None
    error: str | None = None


class CommunicationChannel(Protocol):
    """
    Minimal contract implemented by outbound communication channels.
    """

    name: str

    def send(
        self,
        message: OutboundMessage,
    ) -> DeliveryResult:
        ...