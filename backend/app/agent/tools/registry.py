from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import ValidationError

from agent.observability.tracing import TraceStore, redact
from agent.tools.policies import ToolPolicy
from domain.models import ApprovalRequired, RiskLevel, ToolContext, ToolExecutionError


@dataclass(slots=True)
class RegisteredTool:
    tool: BaseTool
    policy: ToolPolicy
    failures: int = 0
    opened_at: float | None = None


class ToolRegistry:
    """本地 LangChain 工具和 MCP 工具的执行网关。"""

    def __init__(self, traces: TraceStore):
        self._tools: dict[str, RegisteredTool] = {}
        self._traces = traces
        self._results: dict[str, Any] = {}

    def register(self, tool: BaseTool, policy: ToolPolicy | None = None) -> None:
        if tool.name in self._tools:
            raise ValueError(f"工具名称重复： {tool.name}")
        self._tools[tool.name] = RegisteredTool(tool, policy or ToolPolicy())

    @property
    def model_tools(self) -> list[BaseTool]:
        return [item.tool for item in self._tools.values()]

    def describe(self) -> list[dict[str, Any]]:
        return [
            {"name": item.tool.name, "description": item.tool.description,
             "risk": item.policy.risk.value, "requires_approval": item.policy.requires_approval}
            for item in self._tools.values()
        ]

    async def execute(self, name: str, arguments: dict[str, Any], context: ToolContext) -> Any:
        item = self._tools.get(name)
        if item is None:
            raise ToolExecutionError(name, "工具未注册")
        if not context.roles.intersection(item.policy.allowed_roles):
            raise ToolExecutionError(name, "工具策略不允许此操作")
        action_key = self._action_key(name, arguments)
        if item.policy.requires_approval and action_key not in context.approved_actions:
            raise ApprovalRequired(name, redact(arguments), "此操作会修改业务数据，需要明确审批")
        now = time.monotonic()
        if item.opened_at and now - item.opened_at < item.policy.cooldown_seconds:
            raise ToolExecutionError(name, "工具熔断保护已开启", retryable=True)
        if item.opened_at:
            item.opened_at, item.failures = None, 0
        if item.policy.risk != RiskLevel.READ and action_key in self._results:
            return self._results[action_key]
        validated = self._validate(item.tool, arguments)
        async with self._traces.span(context.run_id, f"tool.{name}", {"arguments": validated, "risk": item.policy.risk.value}):
            for attempt in range(1, item.policy.max_attempts + 1):
                try:
                    result = await asyncio.wait_for(item.tool.ainvoke(validated), timeout=item.policy.timeout_seconds)
                    item.failures = 0
                    if item.policy.risk != RiskLevel.READ:
                        self._results[action_key] = result
                    return result
                except ApprovalRequired:
                    raise
                except Exception as exc:
                    item.failures += 1
                    if item.failures >= item.policy.failure_threshold:
                        item.opened_at = time.monotonic()
                    if attempt >= item.policy.max_attempts:
                        raise ToolExecutionError(name, str(exc), retryable=True) from exc
                    await asyncio.sleep(min(0.25 * 2 ** (attempt - 1), 2.0))
        raise ToolExecutionError(name, "工具执行意外结束")

    @staticmethod
    def _validate(tool: BaseTool, arguments: dict[str, Any]) -> dict[str, Any]:
        schema = tool.args_schema
        if schema is None or isinstance(schema, dict):
            return arguments
        try:
            validated = schema.model_validate(arguments)
            return validated.model_dump() if hasattr(validated, "model_dump") else dict(validated)
        except ValidationError as exc:
            raise ToolExecutionError(tool.name, f"参数无效： {exc}") from exc

    @staticmethod
    def _action_key(name: str, arguments: dict[str, Any]) -> str:
        payload = json.dumps(arguments, ensure_ascii=False, sort_keys=True, default=str)
        return f"{name}:{hashlib.sha256(payload.encode()).hexdigest()}"

    @classmethod
    def approval_key(cls, name: str, arguments: dict[str, Any]) -> str:
        return cls._action_key(name, arguments)
