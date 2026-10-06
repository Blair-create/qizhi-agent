import json
import sys
from pathlib import Path
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from infrastructure.llm import get_model
from core.config import settings


def load_mcp_connections(config_path: str) -> dict[str, dict[str, Any]]:
    path = Path(config_path)
    if not path.is_file():
        raise RuntimeError(f"MCP 配置文件不存在：{path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取 MCP 配置文件 {path}：{exc}") from exc
    connections = raw.get("mcpServers", raw) if isinstance(raw, dict) else None
    if not isinstance(connections, dict) or not connections:
        raise RuntimeError("MCP 配置必须是非空对象，或包含非空的 mcpServers 对象")
    normalized = {}
    for server_name, connection in connections.items():
        if not isinstance(server_name, str) or not isinstance(connection, dict):
            raise RuntimeError("每个 MCP Server 都必须使用名称和对象配置")
        item = dict(connection)
        if item.get("command") == "{python}":
            item["command"] = sys.executable
        item.setdefault("transport", "stdio" if item.get("command") else "streamable_http")
        if item["transport"] == "stdio":
            item.setdefault("cwd", str(path.parent))
        normalized[server_name] = item
    return normalized


async def discover_mcp_tools(config_path: str):
    return await MultiServerMCPClient(load_mcp_connections(config_path)).get_tools()


async def create_mcp_agent(config_path: str):
    tools = await MultiServerMCPClient(load_mcp_connections(config_path)).get_tools()
    if not tools:
        raise RuntimeError("已连接 MCP Server，但没有发现任何可用工具")
    graph = create_react_agent(
        model=get_model(settings.DEFAULT_MODEL), tools=tools,
        prompt="你是企业 OA 智能事务助手，只能通过已发现的 MCP 工具访问企业数据。不得编造工具结果。",
        checkpointer=MemorySaver(), name="mcp_assistant",
    )
    return graph, [tool.name for tool in tools]
