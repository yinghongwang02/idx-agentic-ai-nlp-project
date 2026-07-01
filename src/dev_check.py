from src.schemas.intent_schema import PropertyIntent
from src.skills.search_skill import SearchSkill
from src.skills.skill_registry import SkillRegistry
from src.memory.session_memory import SessionMemory


def main() -> None:
    memory = SessionMemory()
    memory.set("last_city", "Irvine")

    registry = SkillRegistry()
    registry.register(SearchSkill())

    search_skill = registry.get("property_search")

    intent = PropertyIntent(
        city=memory.get("last_city"),
        max_price=900000,
        min_bedrooms=3,
    )

    results = search_skill.run(intent)

    print("Registered skills:", registry.list_skills())
    print("Memory last_city:", memory.get("last_city"))
    print("Search results:", [item.listing_key for item in results])


if __name__ == "__main__":
    main()