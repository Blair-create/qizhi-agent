"""后端启动入口。

运行方式（在 backend 目录下）：
    python app/run_server.py

这里使用 uvicorn 启动 FastAPI 应用，并在开发模式下开启热重载。
"""

import asyncio
import sys

import uvicorn
from dotenv import load_dotenv

# 从 backend/.env 加载 API Key、端口、数据库地址等配置。
load_dotenv()

# 必须在加载 .env 后再导入 settings，确保启动进程读取的是最新配置。
from core.config import settings

if __name__ == "__main__":
    if sys.platform == "win32":
        # Windows 下使用 Selector 事件循环，兼容 uvicorn 的开发重载。
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # "main:app" 表示 app/main.py 中名为 app 的 FastAPI 实例。
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.is_dev())
