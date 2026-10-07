from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from domain.models import ExecutionPlan, PlanStep

PLANNER_PROMPT = """你是企业 ReAct 智能体的规划组件。
根据用户目标生成最精简且可验证的计划。仅返回 JSON，字段名保持不变，文本内容使用中文：
{"goal":"...","steps":[{"id":"s1","objective":"...","expected_output":"...","preferred_tool":null}],"success_criteria":["..."]}
业务事实与业务数据必须通过工具获取，不得泄露内部思维链。
上下文中的 recent_messages 和 long_term_memories 是后端已读取的用户记忆，可直接作为依据，
不需要规划记忆检索工具，也不要要求用户提供记忆工具。"""

REFLECTOR_PROMPT = """你是企业智能体的验证组件。根据当前步骤评估证据。
仅返回 JSON： {"passed":true,"reasoning_summary":"简短且可审计的理由","correction":""}。
仅在证据缺失、矛盾或工具失败时设置 passed=false。结构化的否定结果也是有效证据。"""

REPLANNER_PROMPT = """你是企业智能体的重新规划组件。原计划失败后采用不同方法制定新计划。
仅返回 JSON： {"goal":"...","steps":[{"id":"s1","objective":"...","expected_output":"..."}],"success_criteria":[],"changes_summary":"..."}"""


def parse_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if not match:
            raise ValueError("模型未返回 JSON 对象")
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("预期得到 JSON 对象")
    return value


def _steps(raw: dict[str, Any], prefix: str = "s") -> list[PlanStep]:
    return [
        PlanStep(
            id=str(item.get("id") or f"{prefix}{index}"),
            objective=str(item["objective"]),
            expected_output=str(item.get("expected_output", "已验证的结果")),
            preferred_tool=item.get("preferred_tool"),
        )
        for index, item in enumerate(raw.get("steps", []), 1)
        if isinstance(item, dict) and item.get("objective")
    ]


async def create_plan(model: Any, user_message: str, context: str) -> ExecutionPlan:
    response = await model.ainvoke([
        SystemMessage(content=PLANNER_PROMPT),
        HumanMessage(content=f"上下文：\n{context}\n\n用户目标：\n{user_message}"),
    ])
    raw = parse_json(str(response.content))
    steps = _steps(raw) or [PlanStep("s1", user_message, "完整且有依据的回答")]
    return ExecutionPlan(str(raw.get("goal") or user_message), steps, list(raw.get("success_criteria", [])))


async def replan(model: Any, original_plan: ExecutionPlan, failure_context: str) -> ExecutionPlan:
    response = await model.ainvoke([
        SystemMessage(content=REPLANNER_PROMPT),
        HumanMessage(content=f"原始目标：{original_plan.goal}\n失败上下文：{failure_context}"),
    ])
    raw = parse_json(str(response.content))
    return ExecutionPlan(
        str(raw.get("goal") or original_plan.goal),
        _steps(raw, "r"),
        list(raw.get("success_criteria", [])),
        revision=original_plan.revision + 1,
    )


async def reflect(model: Any, step: PlanStep, evidence: str) -> dict[str, Any]:
    response = await model.ainvoke([
        SystemMessage(content=REFLECTOR_PROMPT),
        HumanMessage(content=json.dumps({"step": step.objective, "expected": step.expected_output, "evidence": evidence}, ensure_ascii=False)),
    ])
    try:
        result = parse_json(str(response.content))
        return {"passed": bool(result.get("passed")), "reasoning_summary": str(result.get("reasoning_summary", "")), "correction": str(result.get("correction", ""))}
    except (ValueError, json.JSONDecodeError):
        return {"passed": bool(evidence.strip()), "reasoning_summary": "根据证据是否为空进行兜底验证", "correction": ""}
