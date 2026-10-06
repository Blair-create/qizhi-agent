"""FastAPI 应用装配入口。

本文件负责创建应用、配置跨域，并挂载各个业务路由；具体业务逻辑位于
backend/app/api、backend/app/agent 等目录。
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from datetime import datetime, timezone
from core.config import settings
from infrastructure.mcp import discover_mcp_tools
from bootstrap.runtime import build_harness
from api.runtime_routes import router as runtime_router
from fastapi.middleware.cors import CORSMiddleware


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """在服务启动时发现 MCP 工具并构建 Runtime；未配置 MCP 时使用内置工具。"""
    mcp_tools = []
    if settings.MCP_CONFIG_PATH:
        try:
            mcp_tools = await discover_mcp_tools(settings.MCP_CONFIG_PATH)
            logger.info("MCP 工具已加载：%s", ", ".join(tool.name for tool in mcp_tools))
        except Exception:
            logger.exception("MCP 工具发现失败，服务将使用内置工具继续启动")
    app.state.agent_runtime = build_harness(mcp_tools)
    logger.info("Agent Harness 初始化完成")
    yield


app = FastAPI(
    title="企知 Agent 接口",
    version="1.0.0",
    description="基于 ReAct 范式的企业级 Agent 执行引擎，支持规划、工具调用、记忆、反思、审批和可观测性",
    lifespan=lifespan,
)

# 允许跨域访问。生产环境应将 * 改为指定的前端域名。
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(runtime_router)


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """健康检查接口，返回服务状态和 Runtime 就绪状态。"""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": app.version,
        "runtime": "ready" if hasattr(app.state, "agent_runtime") else "starting",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/agents", tags=["system"])
async def list_agents() -> list[dict]:
    """返回可用的 Agent 列表。当前仅提供单一的企业级 Agent Runtime。"""
    return [{
        "key": "enterprise-agent-runtime",
        "name": "公司通用智能体",
        "description": "基于 ReAct 的企业级 Agent，包含规划、工具调用、记忆、反思、审批流程和完整可观测性"
    }]

