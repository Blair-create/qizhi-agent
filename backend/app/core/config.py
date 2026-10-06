"""应用配置。"""

# 旧版 Pydantic 的导入方式：from pydantic import BaseSettings
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        validate_default=False,
    )
    
    APP_NAME: str = "企知 Agent"
    DEBUG: bool = True
    DATABASE_URL: str | None = None
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEV: bool = True
    
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    # OpenAI 兼容服务的模型名
    OPENAI_MODEL: str | None = None
    
    DEFAULT_MODEL: str | None = None
    
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    CHROMA_PATH: str | None = None
    # MCP Server 配置文件。未配置时不加载 MCP，原有智能体不受影响。
    MCP_CONFIG_PATH: str | None = None
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
    AGENT_STATE_DB: str = "resource/agent_state.db"
    AGENT_TRACE_DB: str = "resource/agent_traces.db"
    AGENT_MAX_STEP_ATTEMPTS: int = 2
    AGENT_RUN_TIMEOUT_SECONDS: float = 180.0
    
    def is_dev(self):
        return self.DEV

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]



settings = Settings()

# 相对资源路径统一以 backend 目录为基准，避免不同启动目录连接到不同数据库。
if settings.DATABASE_URL and settings.DATABASE_URL.startswith("sqlite+aiosqlite:///resource/"):
    relative_db = settings.DATABASE_URL.removeprefix("sqlite+aiosqlite:///")
    settings.DATABASE_URL = f"sqlite+aiosqlite:///{(BACKEND_DIR / relative_db).as_posix()}"

if settings.CHROMA_PATH and not Path(settings.CHROMA_PATH).is_absolute():
    settings.CHROMA_PATH = str((BACKEND_DIR / settings.CHROMA_PATH).resolve())

if settings.MCP_CONFIG_PATH and not Path(settings.MCP_CONFIG_PATH).is_absolute():
    settings.MCP_CONFIG_PATH = str((BACKEND_DIR / settings.MCP_CONFIG_PATH).resolve())


if not Path(settings.AGENT_STATE_DB).is_absolute():
    settings.AGENT_STATE_DB = str((BACKEND_DIR / settings.AGENT_STATE_DB).resolve())
if not Path(settings.AGENT_TRACE_DB).is_absolute():
    settings.AGENT_TRACE_DB = str((BACKEND_DIR / settings.AGENT_TRACE_DB).resolve())
