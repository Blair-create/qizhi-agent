from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent.harness import AgentHarness
from agent.evaluation import EvaluationRunner
from domain.models import RunRequest
from core.config import BACKEND_DIR


router = APIRouter(prefix="/agent", tags=["agent-runtime"])


class AgentRunInput(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    thread_id: str = Field(min_length=1, max_length=128)
    user_id: str = Field(default="anonymous", max_length=128)
    approved_actions: list[str] = Field(default_factory=list)


def runtime(request: Request) -> AgentHarness:
    value = getattr(request.app.state, "agent_runtime", None)
    if value is None:
        raise HTTPException(503, "智能体运行引擎尚未就绪")
    return value


def to_request(value: AgentRunInput) -> RunRequest:
    # API 输入到业务对象之间的适配层
    return RunRequest(value.message, value.thread_id, value.user_id, {"user"}, set(value.approved_actions))


@router.post("/runs")
async def create_run(body: AgentRunInput, request: Request) -> dict[str, Any]:
    result = await runtime(request).run(to_request(body))
    return {
        "run_id": result.run_id,
        "status": result.status.value,
        "answer": result.answer,
        "plan": result.plan,
        "approval": result.approval,
        "error": result.error,
    }


@router.post("/runs/stream")
async def stream_run(body: AgentRunInput, request: Request) -> StreamingResponse:
    agent = runtime(request)

    async def events():
        async for event in agent.stream(to_request(body)):
            payload = {"type": event.type, "run_id": event.run_id, **event.data}
            yield f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
        yield f"data: {json.dumps({'type': 'end'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.get("/runs/{run_id}/trace")
async def get_trace(run_id: str, request: Request) -> dict[str, Any]:
    spans = await runtime(request).traces.get_trace(run_id)
    if not spans:
        raise HTTPException(404, "未找到执行轨迹")
    return {"run_id": run_id, "spans": spans}


@router.get("/tools")
async def list_tools(request: Request) -> dict[str, Any]:
    return {"tools": runtime(request).tools.describe()}


@router.get("/skills")
async def list_skills(request: Request) -> dict[str, Any]:
    return {"skills": runtime(request).skills.describe()}


@router.post("/evaluations/oa-regression")
async def run_regression(request: Request) -> dict[str, Any]:
    """运行 OA 场景回归测试。"""
    runner = EvaluationRunner(runtime(request))
    cases = runner.load(str(BACKEND_DIR / "evals" / "oa_regression.json"))
    return await runner.run(cases)
