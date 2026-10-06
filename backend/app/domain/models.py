"""不依赖 LangChain 或 FastAPI 的稳定领域契约。"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class RiskLevel(StrEnum):
    READ = "read"
    WRITE = "write"
    SENSITIVE = "sensitive"


class RunStatus(StrEnum):
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class PlanStep:
    id: str
    objective: str
    expected_output: str
    preferred_tool: str | None = None
    status: str = "pending"
    attempts: int = 0


@dataclass(slots=True)
class ExecutionPlan:
    goal: str
    steps: list[PlanStep]
    success_criteria: list[str] = field(default_factory=list)
    revision: int = 1


@dataclass(slots=True)
class ToolContext:
    run_id: str
    thread_id: str
    user_id: str
    roles: set[str]
    approved_actions: set[str] = field(default_factory=set)


@dataclass(slots=True)
class RuntimeEvent:
    type: str
    run_id: str
    data: dict[str, Any]


@dataclass(slots=True)
class RunRequest:
    message: str
    thread_id: str
    user_id: str = "anonymous"
    roles: set[str] = field(default_factory=lambda: {"user"})
    approved_actions: set[str] = field(default_factory=set)


@dataclass(slots=True)
class RunResult:
    run_id: str
    status: RunStatus
    answer: str = ""
    plan: dict[str, Any] | None = None
    approval: dict[str, Any] | None = None
    error: str | None = None


class ChatModel(Protocol):
    async def ainvoke(self, messages: list[Any], **kwargs: Any) -> Any: ...


class ApprovalRequired(RuntimeError):
    def __init__(self, tool_name: str, arguments: dict[str, Any], reason: str):
        super().__init__(reason)
        self.tool_name = tool_name
        self.arguments = arguments
        self.reason = reason


class ToolExecutionError(RuntimeError):
    def __init__(self, tool_name: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.tool_name = tool_name
        self.retryable = retryable

__all__ = [
    "ApprovalRequired",
    "ExecutionPlan",
    "PlanStep",
    "RiskLevel",
    "RunRequest",
    "RunResult",
    "RunStatus",
    "RuntimeEvent",
    "ToolContext",
    "ToolExecutionError",
]
