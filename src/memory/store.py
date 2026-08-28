from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any, Protocol


MemoryValue = dict[str, Any]


class MemoryStore(Protocol):
    """
    Storage interface for session-scoped orchestration memory.

    Implementations decide where session data is persisted.
    The Week 9 MVP uses an in-process implementation, while
    future implementations may use Redis or another persistent
    backend.
    """

    def get(
        self,
        session_id: str,
    ) -> MemoryValue | None:
        """
        Return a defensive copy of one session's memory.

        Returns None when the session does not exist.
        """
        ...

    def set(
        self,
        session_id: str,
        value: MemoryValue,
    ) -> None:
        """
        Replace the stored value for one session.
        """
        ...

    def clear(
        self,
        session_id: str,
    ) -> None:
        """
        Remove one session from the store.
        """
        ...


class InMemoryMemoryStore:
    """
    Lightweight process-local MemoryStore implementation.

    Data is isolated by session ID and survives across requests
    only while the current Python process remains alive.
    """

    def __init__(self) -> None:
        self._sessions: dict[
            str,
            MemoryValue,
        ] = {}

        self._lock = RLock()

    def get(
        self,
        session_id: str,
    ) -> MemoryValue | None:
        session_id = self._normalize_session_id(
            session_id
        )

        with self._lock:
            value = self._sessions.get(
                session_id
            )

            if value is None:
                return None

            return deepcopy(value)

    def set(
        self,
        session_id: str,
        value: MemoryValue,
    ) -> None:
        session_id = self._normalize_session_id(
            session_id
        )

        if not isinstance(value, dict):
            raise TypeError(
                "MemoryStore value must be a dict."
            )

        with self._lock:
            self._sessions[
                session_id
            ] = deepcopy(value)

    def clear(
        self,
        session_id: str,
    ) -> None:
        session_id = self._normalize_session_id(
            session_id
        )

        with self._lock:
            self._sessions.pop(
                session_id,
                None,
            )

    @staticmethod
    def _normalize_session_id(
        session_id: str,
    ) -> str:
        if not isinstance(
            session_id,
            str,
        ):
            raise TypeError(
                "session_id must be a string."
            )

        session_id = session_id.strip()

        if not session_id:
            raise ValueError(
                "session_id must not be empty."
            )

        return session_id