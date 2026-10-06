from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from domain.models import RunRequest, RunStatus


@dataclass(slots=True)
class EvalCase:
    id: str
    input: str
    expected_tools: list[str]
    required_terms: list[str]
    forbidden_terms: list[str]


class EvaluationRunner:
    """用于路由、证据和回答的可重复回归评估器。"""

    def __init__(self, runtime: Any):
        self.runtime = runtime

    @staticmethod
    def load(path: str) -> list[EvalCase]:
        return [EvalCase(**item) for item in json.loads(Path(path).read_text(encoding="utf-8"))]

    async def run(self, cases: list[EvalCase]) -> dict[str, Any]:
        rows = []
        for case in cases:
            events = []
            result = await self.runtime.run(
                RunRequest(case.input, f"eval-{uuid4()}", "evaluator", {"user"}), events.append
            )
            used_tools = [event.data["name"] for event in events if event.type == "tool_started"]
            answer_lower = result.answer.lower()
            checks = {
                "completed": result.status == RunStatus.COMPLETED,
                "tools": all(name in used_tools for name in case.expected_tools),
                "required_terms": all(term.lower() in answer_lower for term in case.required_terms),
                "forbidden_terms": all(term.lower() not in answer_lower for term in case.forbidden_terms),
            }
            rows.append({"id": case.id, "passed": all(checks.values()), "checks": checks, "tools": used_tools, "run_id": result.run_id})
        passed = sum(row["passed"] for row in rows)
        return {"total": len(rows), "passed": passed, "pass_rate": passed / len(rows) if rows else 0.0, "cases": rows}
