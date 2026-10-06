from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import asdict
from typing import Any, AsyncIterator, Awaitable, Callable
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool

from agent.memory import SQLiteMemoryStore
from agent.observability import TraceStore
from agent.planning import create_plan, reflect
from agent.skills import SkillRegistry
from agent.tools import ToolRegistry
from core.config import settings
from domain.models import ApprovalRequired, RunRequest, RunResult, RunStatus, RuntimeEvent, ToolContext, ToolExecutionError

Emit = Callable[[RuntimeEvent], Awaitable[None]]


@tool
def ask_user(question: str) -> str:
    """询问缺失的必要用户信息，停止执行且不进行写入。"""
    return question


class ClarificationRequired(Exception):
    pass


class AgentHarness:
    """Agent 生命周期控制器：规划、工具执行、反思、记忆和可观测事件。"""

    def __init__(self, model: Any, memory: SQLiteMemoryStore, traces: TraceStore, tools: ToolRegistry,
                 skills: SkillRegistry | None = None, run_timeout_seconds: float = 180.0):
        self.model, self.memory, self.traces, self.tools = model, memory, traces, tools
        self.skills = skills or SkillRegistry.default()
        self.run_timeout_seconds = run_timeout_seconds

    @classmethod
    def from_runtime(cls, runtime: Any, *, run_timeout_seconds: float = 180.0) -> "AgentHarness":
        return cls(runtime.model, runtime.memory, runtime.traces, runtime.tools, runtime.skills, run_timeout_seconds)

    async def run(self, request: RunRequest, emit: Emit | None = None) -> RunResult:
        try:
            async with asyncio.timeout(self.run_timeout_seconds):
                return await self._run(request, emit)
        except TimeoutError:
            run_id = str(uuid4())
            error = f"Agent 执行超过总时限 {self.run_timeout_seconds:g} 秒"
            if emit:
                result = emit(RuntimeEvent("run_failed", run_id, {"error": error, "reason": "timeout"}))
                if inspect.isawaitable(result):
                    await result
            return RunResult(run_id, RunStatus.FAILED, error=error)

    async def _run(self, request: RunRequest, emit: Emit | None) -> RunResult:
        run_id = str(uuid4())

        async def publish(event_type: str, **data: Any) -> None:
            if emit:
                result = emit(RuntimeEvent(event_type, run_id, data))
                if inspect.isawaitable(result):
                    await result

        await publish("run_started", thread_id=request.thread_id)
        try:
            async with self.traces.span(run_id, "memory.load", {"thread_id": request.thread_id}):
                history, memories = await asyncio.gather(self.memory.recent_messages(request.thread_id), self.memory.recall(request.user_id, request.message))
            context = json.dumps({"recent_messages": history, "long_term_memories": [asdict(item) for item in memories]}, ensure_ascii=False)
            skill = self.skills.select(request.message, request.roles)
            if skill:
                context += "\n匹配业务能力：" + json.dumps(asdict(skill.definition), ensure_ascii=False)
                await publish("skill_selected", name=skill.definition.name, description=skill.definition.description)
            await publish("memory_loaded", short_term_count=len(history), long_term_count=len(memories))
            async with self.traces.span(run_id, "planner", {"goal": request.message}):
                plan = await create_plan(self.model, request.message, context)
            plan_data = asdict(plan)
            await publish("plan_created", plan=plan_data)
            tool_context = ToolContext(run_id, request.thread_id, request.user_id, request.roles, request.approved_actions)
            evidence: list[str] = []
            for step in plan.steps:
                step.status = "running"
                await publish("step_started", step=asdict(step))
                value = await self._step(request, step, context, evidence, tool_context, publish)
                evidence.append(value)
                step.status = "completed"
                await publish("step_completed", step_id=step.id)
            async with self.traces.span(run_id, "finalize"):
                answer = await self._finalize(request.message, context, plan_data, evidence)
            await asyncio.gather(self.memory.append_message(request.thread_id, "user", request.message, run_id), self.memory.append_message(request.thread_id, "assistant", answer, run_id))
            if request.message.startswith(("记住", "remember")):
                await self.memory.remember(request.user_id, "explicit", request.message, {"run_id": run_id})
            await publish("run_completed", answer=answer)
            return RunResult(run_id, RunStatus.COMPLETED, answer=answer, plan=plan_data)
        except ClarificationRequired as exc:
            answer = str(exc)
            await self.memory.append_message(request.thread_id, "user", request.message, run_id)
            await self.memory.append_message(request.thread_id, "assistant", answer, run_id)
            await publish("run_completed", answer=answer, outcome="needs_input")
            return RunResult(run_id, RunStatus.COMPLETED, answer=answer)
        except ApprovalRequired as exc:
            approval = {"tool": exc.tool_name, "arguments": exc.arguments, "reason": exc.reason, "action_key": ToolRegistry.approval_key(exc.tool_name, exc.arguments)}
            await publish("approval_required", **approval)
            return RunResult(run_id, RunStatus.WAITING_APPROVAL, approval=approval)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            await publish("run_failed", error=message)
            return RunResult(run_id, RunStatus.FAILED, error=message)

    async def _step(self, request, step, context, prior, tool_context, publish) -> str:
        correction = ""
        for attempt in range(1, settings.AGENT_MAX_STEP_ATTEMPTS + 1):
            step.attempts = attempt
            prompt = ("执行企业 ReAct 计划步骤。事实必须调用工具，不得编造工具输出；缺少信息时调用 ask_user。\n"
                      f"用户目标：{request.message}\n步骤：{step.objective}\n预期：{step.expected_output}\n上下文：{context}\n已有证据：{prior}\n纠正：{correction}")
            async with self.traces.span(tool_context.run_id, "react.decide", {"step_id": step.id, "attempt": attempt}):
                decision: AIMessage = await self.model.bind_tools([*self.tools.model_tools, ask_user]).ainvoke([SystemMessage(content=prompt), HumanMessage(content=request.message)])
            observations = []
            if decision.tool_calls:
                questions = [call["args"].get("question", "").strip() for call in decision.tool_calls if call["name"] == "ask_user"]
                if questions:
                    raise ClarificationRequired("\n".join(questions))
                for call in decision.tool_calls:
                    await publish("tool_started", name=call["name"], arguments=call["args"], step_id=step.id)
                    try:
                        result = await self.tools.execute(call["name"], call["args"], tool_context)
                    except ToolExecutionError as exc:
                        result = {"error": str(exc), "retryable": exc.retryable}
                    observations.append(f"{call['name']}: {json.dumps(result, ensure_ascii=False, default=str)}")
                    await publish("tool_completed", name=call["name"], result=result, step_id=step.id)
                evidence = "\n".join(observations)
            else:
                evidence = str(decision.content).strip()
            async with self.traces.span(tool_context.run_id, "reflect", {"step_id": step.id, "attempt": attempt}):
                verdict = await reflect(self.model, step, evidence)
            if observations and evidence.strip() and not any(marker in evidence.lower() for marker in ("timeout", "connectionerror", "traceback")):
                verdict["passed"], verdict["correction"] = True, ""
            await publish("reflection", step_id=step.id, **verdict)
            if verdict["passed"]:
                return evidence
            correction = verdict["correction"] or verdict["reasoning_summary"]
            await publish("recovery", step_id=step.id, attempt=attempt)
        raise RuntimeError(f"步骤 {step.id} 在尝试 {settings.AGENT_MAX_STEP_ATTEMPTS} 次后仍未通过验证")

    async def _finalize(self, goal, context, plan, evidence):
        prompt = "仅使用证据和上下文回答用户，默认中文；不得编造或泄露内部推理。\n" + f"目标：{goal}\n计划：{json.dumps(plan, ensure_ascii=False)}\n证据：{json.dumps(evidence, ensure_ascii=False)}\n上下文：{context}"
        response = await self.model.ainvoke([SystemMessage(content=prompt), HumanMessage(content=goal)])
        return str(response.content).strip()

    async def stream(self, request: RunRequest) -> AsyncIterator[RuntimeEvent]:
        queue: asyncio.Queue[RuntimeEvent | None] = asyncio.Queue()
        async def emit(event: RuntimeEvent):
            await queue.put(event)
        async def execute():
            try:
                await self.run(request, emit)
            finally:
                await queue.put(None)
        task = asyncio.create_task(execute())
        try:
            while (event := await queue.get()) is not None:
                yield event
        finally:
            if not task.done():
                task.cancel()
