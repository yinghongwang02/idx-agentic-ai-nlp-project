from __future__ import annotations

import pytest

from src.memory.store import (
    InMemoryMemoryStore,
    MemoryStore,
)


def test_store_saves_and_reads_session():
    store = InMemoryMemoryStore()

    store.set(
        "session-1",
        {
            "last_route": "search",
            "listing_id": "TEST-001",
        },
    )

    result = store.get(
        "session-1"
    )

    assert result == {
        "last_route": "search",
        "listing_id": "TEST-001",
    }


def test_store_isolates_sessions():
    store = InMemoryMemoryStore()

    store.set(
        "session-1",
        {
            "city": "Irvine",
        },
    )

    store.set(
        "session-2",
        {
            "city": "San Diego",
        },
    )

    assert store.get(
        "session-1"
    ) == {
        "city": "Irvine",
    }

    assert store.get(
        "session-2"
    ) == {
        "city": "San Diego",
    }


def test_store_returns_none_for_missing_session():
    store = InMemoryMemoryStore()

    assert store.get(
        "missing-session"
    ) is None


def test_store_replaces_existing_value():
    store = InMemoryMemoryStore()

    store.set(
        "session-1",
        {
            "last_route": "search",
        },
    )

    store.set(
        "session-1",
        {
            "last_route": "market",
        },
    )

    assert store.get(
        "session-1"
    ) == {
        "last_route": "market",
    }


def test_store_clear_removes_only_target_session():
    store = InMemoryMemoryStore()

    store.set(
        "session-1",
        {
            "city": "Irvine",
        },
    )

    store.set(
        "session-2",
        {
            "city": "Pasadena",
        },
    )

    store.clear(
        "session-1"
    )

    assert store.get(
        "session-1"
    ) is None

    assert store.get(
        "session-2"
    ) == {
        "city": "Pasadena",
    }


def test_store_uses_defensive_copies():
    store = InMemoryMemoryStore()

    original = {
        "routes": [
            "search"
        ],
    }

    store.set(
        "session-1",
        original,
    )

    original["routes"].append(
        "market"
    )

    stored = store.get(
        "session-1"
    )

    assert stored == {
        "routes": [
            "search"
        ],
    }

    assert stored is not None

    stored["routes"].append(
        "knowledge"
    )

    assert store.get(
        "session-1"
    ) == {
        "routes": [
            "search"
        ],
    }


def test_store_rejects_empty_session_id():
    store = InMemoryMemoryStore()

    with pytest.raises(
        ValueError,
        match=(
            "session_id must not be empty"
        ),
    ):
        store.set(
            "   ",
            {
                "city": "Irvine",
            },
        )


def test_store_rejects_non_dict_value():
    store = InMemoryMemoryStore()

    with pytest.raises(
        TypeError,
        match=(
            "MemoryStore value must be a dict"
        ),
    ):
        store.set(
            "session-1",
            ["search"],
        )  # type: ignore[arg-type]


def test_in_memory_store_satisfies_protocol():
    store: MemoryStore = (
        InMemoryMemoryStore()
    )

    store.set(
        "session-1",
        {
            "route": "knowledge",
        },
    )

    assert store.get(
        "session-1"
    ) == {
        "route": "knowledge",
    }