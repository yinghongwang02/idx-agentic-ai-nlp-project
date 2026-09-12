from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from src.orchestration.composition import create_orchestrator


def _configure_console_encoding() -> None:
    """
    Keep OpenClaw/PowerShell output UTF-8 friendly on Windows.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def _build_response_payload(
    *,
    query: str,
    session_id: str | None,
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Return only the orchestration metadata OpenClaw may need.

    We intentionally do not serialize the entire LangGraph state because
    capability results may contain Pydantic/domain objects that are not
    JSON-serializable and are unnecessary at the channel boundary.
    """
    return {
        "ok": not bool(state.get("errors")),
        "query": query,
        "session_id": session_id,
        "route": state.get("route"),
        "routes": state.get("routes", []),
        "agents_invoked": state.get("agents_invoked", []),
        "final_response": state.get("final_response", ""),
        "errors": state.get("errors", []),
    }


def run_copilot(
    query: str,
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute one request through the existing IDX Unified Copilot.
    """
    normalized_query = query.strip()

    if not normalized_query:
        raise ValueError("Query must not be empty.")

    orchestrator = create_orchestrator()

    state = orchestrator.invoke(
        normalized_query,
        session_id=session_id,
    )

    return _build_response_payload(
        query=normalized_query,
        session_id=session_id,
        state=state,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Thin OpenClaw adapter for the existing IDX "
            "LangGraph Unified Copilot."
        )
    )

    parser.add_argument(
        "query",
        help="Natural-language real-estate request.",
    )

    parser.add_argument(
        "--session-id",
        default=None,
        help=(
            "Optional session identifier forwarded to the "
            "Unified Copilot."
        ),
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a compact JSON envelope instead of plain response text.",
    )

    return parser.parse_args()


def main() -> int:
    _configure_console_encoding()
    args = parse_args()

    try:
        result = run_copilot(
            args.query,
            session_id=args.session_id,
        )
    except Exception as exc:
        error_payload = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

        if args.json:
            print(
                json.dumps(
                    error_payload,
                    ensure_ascii=False,
                )
            )
        else:
            print(
                "IDX Unified Copilot failed: "
                f"{type(exc).__name__}: {exc}",
                file=sys.stderr,
            )

        return 1

    if args.json:
        print(
            json.dumps(
                result,
                ensure_ascii=False,
                default=str,
            )
        )
    else:
        final_response = result.get(
            "final_response",
            "",
        )

        if final_response:
            print(final_response)
        else:
            print(
                "No response was produced by the IDX Unified Copilot.",
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())