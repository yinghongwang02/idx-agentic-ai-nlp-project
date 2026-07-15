from src.memory.session_memory import SessionMemory


def test_update_stores_meaningful_values() -> None:
    memory = SessionMemory()

    memory.update(
        {
            "city": "Irvine",
            "max_price": 1_200_000,
        }
    )

    assert memory.to_dict() == {
        "city": "Irvine",
        "max_price": 1_200_000,
    }


def test_update_ignores_none_and_empty_values() -> None:
    memory = SessionMemory()

    memory.update(
        {
            "city": "Irvine",
            "max_price": 1_200_000,
        }
    )

    memory.update(
        {
            "city": None,
            "max_price": None,
            "keywords": [],
        }
    )

    assert memory.to_dict() == {
        "city": "Irvine",
        "max_price": 1_200_000,
    }


def test_new_scalar_value_overrides_old_value() -> None:
    memory = SessionMemory()

    memory.update({"city": "Irvine"})
    memory.update({"city": "Pasadena"})

    assert memory.get("city") == "Pasadena"


def test_keywords_are_merged_and_deduplicated() -> None:
    memory = SessionMemory()

    memory.update({"keywords": ["garage"]})
    memory.update({"keywords": ["pool", "garage"]})

    assert memory.get("keywords") == ["garage", "pool"]


def test_merge_does_not_mutate_memory() -> None:
    memory = SessionMemory()
    memory.update({"city": "Irvine"})

    merged = memory.merge(
        {
            "max_price": 1_200_000,
            "keywords": ["garage"],
        }
    )

    assert merged == {
        "city": "Irvine",
        "max_price": 1_200_000,
        "keywords": ["garage"],
    }

    assert memory.to_dict() == {
        "city": "Irvine",
    }


def test_unknown_fields_are_ignored() -> None:
    memory = SessionMemory()

    memory.update(
        {
            "city": "Irvine",
            "internal_debug_value": "do not store",
        }
    )

    assert memory.to_dict() == {
        "city": "Irvine",
    }


def test_to_dict_returns_defensive_copy() -> None:
    memory = SessionMemory()
    memory.update({"keywords": ["garage"]})

    snapshot = memory.to_dict()
    snapshot["keywords"].append("pool")

    assert memory.get("keywords") == ["garage"]


def test_clear_removes_all_values() -> None:
    memory = SessionMemory()
    memory.update({"city": "Irvine"})

    memory.clear()

    assert memory.to_dict() == {}
    assert memory.is_empty() is True