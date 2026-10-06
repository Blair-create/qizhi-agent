from __future__ import annotations

from typing import Any

from .base import Skill, SkillDefinition
from .knowledge import enterprise_qa_skill
from .oa import approval_skill, leave_skill


class SkillRegistry:
    """已安装技能的注册表和轻量级路由器。"""

    def __init__(self, skills: list[Skill] | None = None):
        self._skills: dict[str, Skill] = {}
        for skill in skills or []:
            self.register(skill)

    def register(self, skill: Skill) -> None:
        name = skill.definition.name
        if name in self._skills:
            raise ValueError(f"Skill 名称重复：{name}")
        self._skills[name] = skill

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def all(self) -> list[Skill]:
        return list(self._skills.values())

    def select(self, message: str, roles: set[str] | None = None) -> Skill | None:
        roles = roles or {"user"}
        candidates = [
            skill
            for skill in self._skills.values()
            if skill.matches(message)
            and (not skill.definition.required_roles or roles.intersection(skill.definition.required_roles))
        ]
        return max(candidates, key=lambda item: item.definition.priority, default=None)

    def describe(self) -> list[dict[str, Any]]:
        return [
            {
                "name": skill.definition.name,
                "description": skill.definition.description,
                "triggers": list(skill.definition.triggers),
                "tools": list(skill.definition.tool_names),
                "required_roles": list(skill.definition.required_roles),
            }
            for skill in self._skills.values()
        ]

    @classmethod
    def default(cls) -> "SkillRegistry":
        """按业务领域分组的内置技能。"""
        return cls([leave_skill, approval_skill, enterprise_qa_skill])
