from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from src.communication.email_draft_agent import (
    EmailDraft,
)


ApprovalStatus = Literal[
    "approved",
    "rejected",
]


@dataclass(frozen=True)
class EmailApprovalRecord:
    """
    Immutable record of an explicit human decision on an email draft.

    The original EmailDraft remains pending_approval. This record
    captures the downstream human decision separately so draft
    generation and approval remain different responsibilities.
    """

    draft: EmailDraft
    status: ApprovalStatus

    decided_by: str
    decided_at: datetime

    reason: str | None = None

    @property
    def is_approved(self) -> bool:
        return self.status == "approved"

    @property
    def is_rejected(self) -> bool:
        return self.status == "rejected"


class EmailApprovalGate:
    """
    Human-in-the-loop approval boundary for outbound email.

    This component never sends email.

    Responsibilities:
    - require an explicit human identity;
    - approve or reject a pending EmailDraft;
    - create an immutable audit record.

    Outbound authorization is handled separately by
    OutboundSafetyGuard.
    """

    def approve(
        self,
        draft: EmailDraft,
        *,
        decided_by: str,
    ) -> EmailApprovalRecord:
        self._validate_draft(draft)

        actor = self._normalize_actor(
            decided_by
        )

        return EmailApprovalRecord(
            draft=draft,
            status="approved",
            decided_by=actor,
            decided_at=self._utc_now(),
        )

    def reject(
        self,
        draft: EmailDraft,
        *,
        decided_by: str,
        reason: str | None = None,
    ) -> EmailApprovalRecord:
        self._validate_draft(draft)

        actor = self._normalize_actor(
            decided_by
        )

        normalized_reason = str(
            reason or ""
        ).strip()

        return EmailApprovalRecord(
            draft=draft,
            status="rejected",
            decided_by=actor,
            decided_at=self._utc_now(),
            reason=(
                normalized_reason
                if normalized_reason
                else None
            ),
        )

    @staticmethod
    def _validate_draft(
        draft: EmailDraft,
    ) -> None:
        if not isinstance(
            draft,
            EmailDraft,
        ):
            raise TypeError(
                "Approval requires an EmailDraft."
            )

        if (
            draft.status
            != "pending_approval"
        ):
            raise ValueError(
                "Only pending email drafts "
                "can enter the approval gate."
            )

    @staticmethod
    def _normalize_actor(
        decided_by: str,
    ) -> str:
        actor = str(
            decided_by or ""
        ).strip()

        if not actor:
            raise ValueError(
                "Approval decision requires "
                "an explicit human actor."
            )

        return actor

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(
            timezone.utc
        )