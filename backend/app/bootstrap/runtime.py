from __future__ import annotations

from typing import Any

from agent.harness import AgentHarness
from agent.memory import SQLiteMemoryStore
from agent.observability import TraceStore
from agent.skills import SkillRegistry
from agent.tools import ToolPolicy, ToolRegistry, search_handbook
from infrastructure.llm import get_model
from core.config import settings


def build_harness(extra_tools: list[Any] | None = None) -> AgentHarness:
    """根据基础设施适配器和策略组装生产级智能体。"""
    memory = SQLiteMemoryStore(settings.AGENT_STATE_DB)
    traces = TraceStore(settings.AGENT_TRACE_DB)
    registry = ToolRegistry(traces)
    registry.register(search_handbook, ToolPolicy())
    for tool in extra_tools or []:
        metadata = getattr(tool, "metadata", None) or {}
        inferred_write = tool.name.startswith(("add_", "create_", "submit_", "update_", "delete_", "send_", "approve_", "reject_"))
        risk = metadata.get("risk", "write" if inferred_write else "read")
        registry.register(tool, ToolPolicy(requires_approval=risk != "read"))
    return AgentHarness(
        get_model(settings.DEFAULT_MODEL), memory, traces, registry,
        skills=SkillRegistry.default(), run_timeout_seconds=settings.AGENT_RUN_TIMEOUT_SECONDS,
    )
