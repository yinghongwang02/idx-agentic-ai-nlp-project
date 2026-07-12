from src.memory.session_memory import SessionMemory


def main() -> None:
    memory = SessionMemory()

    print("=" * 70)
    print("Turn 1: Find townhouses in Irvine")
    memory.update(
        {
            "city": "Irvine",
            "property_type": "Townhouse",
        }
    )
    print(memory.to_dict())

    print("=" * 70)
    print("Turn 2: Under 1.2 million")
    second_turn = {
        "city": None,
        "property_type": None,
        "max_price": 1_200_000,
    }

    merged_intent = memory.merge(second_turn)
    print("Merged:", merged_intent)

    memory.update(second_turn)
    print("Memory:", memory.to_dict())

    print("=" * 70)
    print("Turn 3: At least 3 bedrooms with a garage")

    third_turn = {
        "city": None,
        "max_price": None,
        "min_bedrooms": 3,
        "keywords": ["garage"],
    }

    merged_intent = memory.merge(third_turn)
    print("Merged:", merged_intent)

    memory.update(third_turn)
    print("Memory:", memory.to_dict())

    print("=" * 70)
    print("Turn 4: Also include a pool and a garage")

    fourth_turn = {
        "keywords": ["pool", "garage"],
    }

    merged_intent = memory.merge(fourth_turn)
    print("Merged:", merged_intent)

    memory.update(fourth_turn)
    print("Memory:", memory.to_dict())

    print("=" * 70)
    print("Unknown fields should not be stored")
    memory.update(
        {
            "internal_debug_value": "should not be saved",
            "random_field": 123,
        }
    )
    print(memory.to_dict())

    print("=" * 70)
    print("Clear memory")
    memory.clear()
    print(memory.to_dict())
    print("Is empty:", memory.is_empty())


if __name__ == "__main__":
    main()