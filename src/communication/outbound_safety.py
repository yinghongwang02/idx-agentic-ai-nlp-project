from __future__ import annotations

from dataclasses import dataclass, field

from src.communication.email_approval import (
    EmailApprovalRecord,
)


@dataclass(frozen=True)
class OutboundSafetyResult:
    """
    Result of outbound email safety validation.
    """

    allowed: bool
    reasons: tuple[str, ...] = field(
        default_factory=tuple
    )


class OutboundSafetyGuard:
    """
    Final safety boundary before an email sender is allowed
    to perform an outbound action.

    Safety rules:
    - explicit approval is mandatory;
    - rejected drafts are never sendable;
    - recipient must be present and plausibly email-shaped;
    - subject and body must not be empty;
    - multiple recipients are blocked in the MVP to avoid
      accidental bulk outbound actions.

    This class does not send email.
    """

    def check(
        self,
        approval: EmailApprovalRecord,
    ) -> OutboundSafetyResult:
        reasons: list[str] = []

        if not isinstance(
            approval,
            EmailApprovalRecord,
        ):
            return OutboundSafetyResult(
                allowed=False,
                reasons=(
                    "Missing valid email approval record.",
                ),
            )

        if not approval.is_approved:
            reasons.append(
                "Email has not been explicitly approved."
            )

        draft = approval.draft

        recipient = str(
            draft.to or ""
        ).strip()

        subject = str(
            draft.subject or ""
        ).strip()

        body = str(
            draft.body or ""
        ).strip()

        if not recipient:
            reasons.append(
                "Email recipient is empty."
            )

        elif not self._looks_like_email(
            recipient
        ):
            reasons.append(
                "Email recipient is invalid."
            )

        if self._looks_like_multiple_recipients(
            recipient
        ):
            reasons.append(
                "Multiple recipients are not allowed "
                "by the current outbound safety policy."
            )

        if not subject:
            reasons.append(
                "Email subject is empty."
            )

        if not body:
            reasons.append(
                "Email body is empty."
            )

        if (
            draft.status
            != "pending_approval"
        ):
            reasons.append(
                "Email draft has an unexpected "
                "lifecycle status."
            )

        return OutboundSafetyResult(
            allowed=not reasons,
            reasons=tuple(reasons),
        )

    def require_safe(
        self,
        approval: EmailApprovalRecord,
    ) -> None:
        """
        Raise instead of returning a blocked result.

        Intended for sender implementations:

            guard.require_safe(approval)
            sender.send(...)
        """

        result = self.check(
            approval
        )

        if not result.allowed:
            message = "; ".join(
                result.reasons
            )

            raise PermissionError(
                "Outbound email blocked: "
                f"{message}"
            )

    @staticmethod
    def _looks_like_email(
        recipient: str,
    ) -> bool:
        if not recipient:
            return False

        if recipient.count("@") != 1:
            return False

        local_part, domain = (
            recipient.split("@", 1)
        )

        if not local_part:
            return False

        if not domain:
            return False

        if "." not in domain:
            return False

        if any(
            char.isspace()
            for char in recipient
        ):
            return False

        return True

    @staticmethod
    def _looks_like_multiple_recipients(
        recipient: str,
    ) -> bool:
        return (
            "," in recipient
            or ";" in recipient
        )