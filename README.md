# 企知 Agent

面向企业办公场景的全栈智能体应用，提供中文对话、任务规划、工具执行、反思验证、写操作确认和执行过程展示，适合本地开发、架构学习和功能演示。

- 前端：Next.js 14、React 18、TypeScript、Ant Design
- 后端：FastAPI、LangChain、LangGraph、SQLite、Chroma、MCP
- 模型：支持 OpenAI 及兼容 OpenAI API 的服务
- 运行方式：前后端本地分开启动，后端通过 SSE 推送智能体运行事件

当前项目默认用于本地开发和演示。用户身份、工具审批参数和动作摘要不能替代生产环境中的认证、授权与审批审计。

## 功能

- 规划、行动、观察、反思的任务执行循环，失败后在限定次数内重试。
- 本地员工手册检索，以及通过 MCP 扩展的员工、部门和请假业务工具。
- 写操作确认、工具权限策略、超时重试、熔断与进程内结果去重。
- SQLite 对话记录、长期记忆与执行轨迹，SSE 推送执行事件。
- 中文界面、模型提示词、注释及开发文档，附带离线单元测试与回归数据集。

## 环境要求

- Python 3.13 和 uv 0.12.10
- Node.js 22 和 pnpm 10.17.1
- OpenAI API 或兼容 OpenAI API 的模型服务

本仓库不附带 Node.js、Python、依赖目录或运行数据库。

## 快速开始

以下命令以 Windows PowerShell 为例。macOS/Linux 使用对应的 `cp` 和路径写法即可。

### 后端

```powershell
cd backend
uv sync --locked
Copy-Item .env.example .env
Copy-Item mcp_servers.oa.example.json mcp_servers.json
```

编辑 `backend/.env`，至少配置模型服务：

```dotenv
OPENAI_API_KEY=填写你的密钥
OPENAI_BASE_URL=https://api.openai.com/v1
DEFAULT_MODEL=gpt-5.6-sol
```

`MCP_CONFIG_PATH=mcp_servers.json` 为可选配置。启用员工和请假工具时，保留该配置并按需修改 `backend/mcp_servers.json`；不使用 MCP 时可以留空。

首次启动演示数据时执行：

```powershell
uv run python resource/generate_data.py
uv run python app/run_server.py
```

数据生成脚本会重建员工和部门表，只适用于初始化或重置演示数据。

接口文档：<http://127.0.0.1:8000/docs>；健康检查：<http://127.0.0.1:8000/health>。

### 前端

在另一个终端，从项目根目录执行：

```powershell
cd frontend
Copy-Item .env.example .env.local
pnpm install --frozen-lockfile
pnpm dev
```

浏览器访问 <http://localhost:3000/chat>。也可以在项目根目录运行 `./start-frontend.ps1` 启动前端开发服务。

### 员工手册检索

员工手册检索使用 `OPENAI_EMBEDDING_MODEL` 生成向量，向量库路径由 `CHROMA_PATH` 配置。仓库不分发真实员工手册和已生成的向量索引；请只导入拥有合法使用权限的资料，并将其写入 Chroma 的 `handbook` 集合。

## 目录

```text
backend/app/
  agent/              智能体循环、规划、工具、记忆、评估和观测
  api/                FastAPI 路由
  bootstrap/          运行时初始化
  core/               配置
  domain/             领域模型
  infrastructure/     LLM、MCP、RAG 等基础设施
backend/mcp_servers/  员工与请假业务 MCP 服务
backend/resource/     SQL、数据生成脚本和本地运行数据目录
backend/tests/        离线单元测试
backend/evals/        回归评估数据集
frontend/app/         Next.js 页面、聊天组件和 SSE 客户端
.github/workflows/    GitHub Actions 检查流程
docs/                 项目说明文档
```

## 接口

| 接口 | 用途 |
| --- | --- |
| `POST /agent/runs` | 非流式执行任务 |
| `POST /agent/runs/stream` | 流式执行任务 |
| `GET /agent/runs/{run_id}/trace` | 查询执行轨迹 |
| `GET /agent/tools` | 查询工具及策略 |
| `GET /health`、`GET /agents` | 健康状态与智能体列表 |

写操作返回 `approval_required` 事件，前端确认后通过 `approved_actions` 重试。动作键是工具名和参数的确定性摘要，并非不可伪造的授权令牌；真实部署需要可信身份认证与服务端审批记录。

## 检查与维护

```powershell
cd frontend
pnpm typecheck
pnpm build
cd ../backend
$env:PYTHONPATH="app"
uv run --locked python -m unittest discover -s tests -p "test_*.py" -v
```

GitHub Actions 对推送和拉取请求执行前端类型检查、构建及后端语法检查、离线测试。在线回归评估需要模型与业务服务，不在 CI 中自动执行。

`Browserslist: browsers data (caniuse-lite) is ... old` 是浏览器兼容性数据库过期提示，不是启动失败。在 `frontend` 目录使用 `pnpm dlx update-browserslist-db@latest` 更新并提交锁文件；若系统没有 npm 或更新器无法调用 pnpm，可直接执行 `pnpm up --depth=9999 --no-save caniuse-lite`。

## 贡献与许可

参阅 [贡献指南](CONTRIBUTING.md)、[安全说明](SECURITY.md)、[许可中文说明](docs/许可证说明.md) 与 [第三方依赖说明](THIRD_PARTY_NOTICES.md)。本项目代码采用 [MIT 许可证](LICENSE)。
