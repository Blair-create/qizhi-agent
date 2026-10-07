# 企知 Agent

企知 Agent 是一个面向企业办公场景的全栈智能体应用，提供中文对话、任务规划、工具调用、反思验证、写操作确认和执行轨迹展示。项目适合本地开发、架构学习和功能演示。

- **前端**：Next.js 14、React 18、TypeScript、Ant Design
- **后端**：FastAPI、LangChain、LangGraph、SQLite、Chroma、MCP
- **模型**：OpenAI 或兼容 OpenAI API 的模型服务
- **运行方式**：前后端分别启动；后端通过 SSE 推送智能体运行事件

项目默认面向本地开发和演示。当前的用户身份、工具审批参数和动作摘要不能替代生产环境的认证、授权和审批审计。

## 功能

- 规划、行动、观察、反思的任务执行循环，支持限定次数内重试和超时控制。
- 内置员工手册检索技能；可通过 MCP 扩展员工、部门和请假业务工具。
- 工具风险策略和写操作审批；执行轨迹写入 SQLite，前端实时展示运行事件。
- SQLite 对话记忆、长期记忆和运行追踪。
- 可查询工具、技能和 Agent 状态，并提供 OA 场景回归评估接口。

## 环境要求

- Python 3.13
- uv 0.12.10
- Node.js 22
- pnpm 10.17.1
- OpenAI 或兼容 OpenAI API 的模型服务

仓库不要求提交 Python/Node 依赖目录。运行时数据库、Chroma 索引和本地环境文件也应保留在本地。

## 快速开始

以下命令以 Windows PowerShell 为例；macOS/Linux 请使用对应的复制文件命令和路径写法。

### 1. 配置并启动后端

```powershell
cd backend
uv sync --locked
Copy-Item .env.example .env
Copy-Item mcp_servers.example.json mcp_servers.json
```

编辑 `backend/.env`。至少需要配置模型服务：

```dotenv
OPENAI_API_KEY=填写你的密钥
OPENAI_BASE_URL=https://api.openai.com/v1
DEFAULT_MODEL=gpt-5.6-sol
```

常用配置如下：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///resource/database.db` | 业务数据库；也支持 MySQL URL |
| `AGENT_STATE_DB` | `resource/agent_state.db` | 对话记忆数据库 |
| `AGENT_TRACE_DB` | `resource/agent_traces.db` | 执行轨迹数据库 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | 员工手册检索使用的本地 Ollama 地址 |
| `OLLAMA_EMBEDDING_MODEL` | `bge-m3` | 员工手册向量检索使用的 Ollama embedding 模型 |
| `CHROMA_PATH` | `resource/chroma_db` | Chroma 持久化目录 |
| `MCP_CONFIG_PATH` | 空 | MCP 配置文件；为空时只使用内置工具 |
| `CORS_ORIGINS` | 本地 3000/3001 端口 | 允许访问后端的前端来源 |
| `HOST` / `PORT` | `127.0.0.1` / `8000` | 后端监听地址和端口 |

相对路径均以 `backend` 目录为基准。需要启用 MCP 时，将 `MCP_CONFIG_PATH=mcp_servers.json` 写入 `backend/.env`；不使用 MCP 时保持为空即可。

首次准备 OA 演示数据时执行：

```powershell
uv run python resource/generate_data.py
```

该脚本会重建 `resource/database.db` 中的 `departments` 和 `employees` 表，并生成演示员工数据；仅适用于初始化或重置本地演示数据。MCP 服务还会按需创建请假和员工审计表。

启动后端：

```powershell
uv run python app/run_server.py
```

开发模式默认开启 Uvicorn 热重载。接口文档位于 <http://127.0.0.1:8000/docs>，健康检查位于 <http://127.0.0.1:8000/health>。

### 2. 配置并启动前端

在另一个终端执行：

```powershell
cd frontend
Copy-Item .env.example .env.local
pnpm install --frozen-lockfile
pnpm dev
```

`frontend/.env.local` 中的 `NEXT_PUBLIC_API_BASE_URL` 应指向后端地址，默认值为 `http://127.0.0.1:8000`。当前聊天页面可从 <http://localhost:3000/> 或 <http://localhost:3000/chat> 访问。

也可以在项目根目录执行：

```powershell
.\start-frontend.ps1
```

该脚本会优先使用 PATH 中的 pnpm，也支持通过 `CODEX_NODE_RUNTIME` 指定本地 Node 运行时目录。

### 3. 员工手册检索

内置 `search_handbook` 工具从 Chroma 的 `handbook` 集合检索内容，并使用本地 Ollama 的 `OLLAMA_EMBEDDING_MODEL` 生成查询向量。默认模型为 `bge-m3`，启动后端前请确认 Ollama 正在运行并已下载模型：

```bash
ollama pull bge-m3
```

仓库只提供检索代码，不提供通用的 PDF 导入命令；请使用拥有合法使用权限的资料建立该集合，并确保 `CHROMA_PATH` 与服务启动时一致。项目默认的 `backend/resource/chroma_db` 已按 1024 维 `bge-m3` 向量建立；如果更换 embedding 模型，需要重新构建 Chroma 索引。缺少集合内容时，应用仍可启动，但检索不会返回有效制度内容。

## 项目结构

```text
backend/
  app/
    agent/              智能体 Harness、规划、技能、工具、记忆、评估和观测
    api/                FastAPI 运行时路由
    bootstrap/          Runtime 组装
    core/               配置和路径处理
    domain/             请求、结果和领域模型
    infrastructure/     LLM、MCP、RAG 适配器
    main.py             FastAPI 应用入口
    run_server.py       Uvicorn 启动入口
  mcp_servers/          OA 业务 MCP 服务
  resource/             SQL、演示数据脚本和本地运行数据目录
  evals/                OA 回归评估数据集
  tests/                离线单元测试
  .env.example          后端配置模板
frontend/
  app/                  Next.js 页面、布局、聊天组件和 SSE 客户端
  package.json          前端脚本和依赖
  .env.example          前端配置模板
docs/                    项目说明文档
.github/workflows/       GitHub Actions 检查流程
start-frontend.ps1       根目录前端启动脚本
```

## HTTP 接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/health` | 健康状态和 Runtime 就绪状态 |
| `GET` | `/agents` | 查询可用 Agent |
| `POST` | `/agent/runs` | 非流式执行任务 |
| `POST` | `/agent/runs/stream` | 以 SSE 流式执行任务 |
| `GET` | `/agent/runs/{run_id}/trace` | 查询执行轨迹 |
| `GET` | `/agent/tools` | 查询工具及风险策略 |
| `GET` | `/agent/skills` | 查询已注册技能 |
| `POST` | `/agent/evaluations/oa-regression` | 运行 `backend/evals/oa_regression.json` 中的 OA 回归用例 |

写操作会先返回 `approval_required` 事件。前端确认后，在下一次请求的 `approved_actions` 中提交服务端返回的动作键。动作键是工具名和参数的确定性摘要，不是不可伪造的授权令牌；真实部署仍需可信身份认证和服务端审批记录。

## 检查与维护

前端检查：

```powershell
cd frontend
pnpm typecheck
pnpm build
```

后端检查：

```powershell
cd backend
$env:PYTHONPATH="app"
uv run --locked python -m compileall -q app mcp_servers tests
uv run --locked python -m unittest discover -s tests -p "test_*.py" -v
```

GitHub Actions 在推送、拉取请求和手动触发时执行相同的前端类型检查、构建、后端语法检查和离线单元测试。OA 在线回归评估需要模型服务和业务工具，不会在 CI 中自动执行。

`Browserslist: browsers data (caniuse-lite) is ... old` 是兼容性数据库过期提示，不代表启动失败。需要更新时，在 `frontend` 目录执行 `pnpm dlx update-browserslist-db@latest`，并按变更提交锁文件。

## 贡献与许可

参阅 [贡献指南](CONTRIBUTING.md)、[安全说明](SECURITY.md)、[许可中文说明](docs/许可证说明.md) 和 [第三方依赖说明](THIRD_PARTY_NOTICES.md)。项目代码采用 [MIT 许可证](LICENSE)。
