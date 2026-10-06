import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from domain.models import ApprovalRequired, RiskLevel, RunStatus, ToolContext, RunRequest
from agent.harness import AgentHarness
from agent.memory import SQLiteMemoryStore
from agent.observability import TraceStore
from agent.tools import ToolPolicy, ToolRegistry


@tool
async def lookup_employee(name: str) -> dict:
    """查询测试员工。"""
    return {"name": name, "department": "研发部门"}


@tool
async def update_employee(name: str) -> dict:
    """更新测试员工。"""
    return {"updated": name}


class ScriptedModel:
    def __init__(self):
        self.phase = 0

    def bind_tools(self, _tools):
        return self

    async def ainvoke(self, messages, **_kwargs):
        system = str(messages[0].content)
        if "规划组件" in system:
            return AIMessage(content=json.dumps({
                "goal": "查询员工", "steps": [{"id": "s1", "objective": "查询 Alice", "expected_output": "record"}],
                "success_criteria": ["已返回记录"],
            }))
        if "验证组件" in system:
            return AIMessage(content='{"passed":true,"reasoning_summary":"工具返回了有依据的记录","correction":""}')
        if "回答用户" in system:
            return AIMessage(content="Alice 在研发部门工作。")
        return AIMessage(content="", tool_calls=[{"name": "lookup_employee", "args": {"name": "Alice"}, "id": "call-1"}])


class AgentRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        root = Path(self.temp.name)
        self.memory = SQLiteMemoryStore(str(root / "memory.db"))
        self.traces = TraceStore(str(root / "traces.db"))
        self.registry = ToolRegistry(self.traces)

    def tearDown(self):
        self.temp.cleanup()

    def test_memory_persists_and_recalls(self):
        async def verify():
            await self.memory.append_message("thread", "user", "hello", "run")
            await self.memory.remember("user", "preference", "偏好简洁的 Python 示例")
            self.assertEqual((await self.memory.recent_messages("thread"))[0]["content"], "hello")
            recalled = await self.memory.recall("user", "Python 示例")
            self.assertEqual(recalled[0].kind, "preference")
        asyncio.run(verify())

    def test_write_tool_requires_approval(self):
        self.registry.register(update_employee, ToolPolicy(risk=RiskLevel.WRITE, requires_approval=True))

        async def verify():
            context = ToolContext("run", "thread", "user", {"user"})
            with self.assertRaises(ApprovalRequired) as caught:
                await self.registry.execute("update_employee", {"name": "Alice"}, context)
            context.approved_actions.add(caught.exception.tool_name + ":invalid")
            context.approved_actions = {self.registry.approval_key("update_employee", {"name": "Alice"})}
            result = await self.registry.execute("update_employee", {"name": "Alice"}, context)
            self.assertEqual(result["updated"], "Alice")
        asyncio.run(verify())

    def test_full_plan_act_reflect_memory_and_trace_loop(self):
        self.registry.register(lookup_employee)
        runtime = AgentHarness(ScriptedModel(), self.memory, self.traces, self.registry)

        async def verify():
            events = []
            result = await runtime.run(RunRequest("Alice 在哪个部门工作？", "thread", "user"), events.append)
            self.assertEqual(result.status, RunStatus.COMPLETED)
            self.assertIn("研发部门", result.answer)
            event_types = {event.type for event in events}
            self.assertTrue({"plan_created", "tool_started", "reflection", "run_completed"}.issubset(event_types))
            trace_names = {span["name"] for span in await self.traces.get_trace(result.run_id)}
            self.assertTrue({"planner", "react.decide", "tool.lookup_employee", "reflect", "finalize"}.issubset(trace_names))
            self.assertEqual(len(await self.memory.recent_messages("thread")), 2)
        asyncio.run(verify())


if __name__ == "__main__":
    unittest.main()
