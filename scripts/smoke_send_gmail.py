from __future__ import annotations

import argparse
import sys

from src.communication.email_approval import EmailApprovalGate
from src.communication.email_draft_agent import EmailDraft
from src.communication.gmail_email_channel import SafeGmailEmailSender


CONFIRMATION_PHRASE = "SEND REAL EMAIL"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Manually send one approved Gmail smoke-test email "
            "through the real Gmail API."
        )
    )

    parser.add_argument(
        "--to",
        required=True,
        help="Recipient email address for the smoke test.",
    )

    parser.add_argument(
        "--subject",
        default="IDX Agentic AI Gmail Smoke Test",
        help="Email subject.",
    )

    parser.add_argument(
        "--body",
        default=(
            "This is a real Gmail API smoke-test message from the "
            "IDX Agentic AI email workflow.\n\n"
            "The message was sent only after explicit human approval "
            "and outbound safety validation."
        ),
        help="Plain-text email body.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    draft = EmailDraft(
        to=args.to.strip(),
        subject=args.subject.strip(),
        body=args.body,
        metadata={
            "draft_type": "gmail_smoke_test",
            "delivery_mode": "real_gmail",
        },
    )

    print()
    print("=" * 72)
    print("REAL GMAIL SMOKE TEST")
    print("=" * 72)
    print("This script will send a REAL email through the Gmail API.")
    print()
    print(f"To:      {draft.to}")
    print(f"Subject: {draft.subject}")
    print()
    print("Body:")
    print("-" * 72)
    print(draft.body)
    print("-" * 72)
    print(f"Draft status: {draft.status}")
    print()

    confirmation = input(
        f'Type "{CONFIRMATION_PHRASE}" to approve and send: '
    ).strip()

    if confirmation != CONFIRMATION_PHRASE:
        print()
        print("Approval not granted. No email was sent.")
        return 0

    approval = EmailApprovalGate().approve(
        draft,
        decided_by="manual-gmail-smoke-test",
    )

    print()
    print("Explicit approval recorded.")
    print("Running outbound safety and Gmail delivery...")

    sender = SafeGmailEmailSender()

    try:
        result = sender.send_approved(
            approval,
            session_id="manual-gmail-smoke-test",
        )
    except PermissionError as exc:
        print()
        print("Outbound safety BLOCKED the send.")
        print(f"Reason: {exc}")
        return 1
    except Exception as exc:
        print()
        print("Unexpected failure before delivery completed.")
        print(f"Error: {exc}")
        return 1

    print()
    print("=" * 72)
    print("DELIVERY RESULT")
    print("=" * 72)
    print(f"Success:    {result.success}")
    print(f"Channel:    {result.channel}")
    print(f"Recipient:  {result.recipient}")
    print(f"Message ID: {result.message_id}")
    print(f"Error:      {result.error}")
    print()

    if result.success:
        print(
            "Real Gmail smoke test PASSED. "
            "Check the sender's Sent folder and the recipient inbox."
        )
        return 0

    print("Real Gmail smoke test FAILED.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
