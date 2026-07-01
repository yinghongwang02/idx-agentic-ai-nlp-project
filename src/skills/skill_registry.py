from src.skills.base_skill import BaseSkill


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> BaseSkill:
        if name not in self._skills:
            raise KeyError(f"Skill not found: {name}")

        return self._skills[name]

    def list_skills(self) -> list[str]:
        return list(self._skills.keys())