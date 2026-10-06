from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


SkillHandler = Callable[["SkillContext", dict[str, Any]], Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    """用于路由、提示、授权和可观测性的元数据。"""

    name: str
    description: str
    triggers: tuple[str, ...] = ()
    tool_names: tuple[str, ...] = ()
    required_roles: tuple[str, ...] = ()
    priority: int = 0


@dataclass(slots=True)
class SkillContext:
    """提供给技能处理器的依赖，不与 FastAPI 耦合。"""

    tools: Any
    tool_context: Any
    memory: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Skill:
    """由一个或多个已注册工具组成的业务能力。"""

    definition: SkillDefinition

    def __init__(self, definition: SkillDefinition, handler: SkillHandler | None = None):
        self.definition = definition
        self.handler = handler

    def matches(self, message: str) -> bool:
        normalized = message.casefold()
        return any(trigger.casefold() in normalized for trigger in self.definition.triggers)

    async def execute(self, context: SkillContext, arguments: dict[str, Any]) -> Any:
        if self.handler is None:
            raise RuntimeError(f"Skill {self.definition.name} 没有配置执行处理器")
        return await self.handler(context, arguments)
