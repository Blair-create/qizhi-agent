from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from contextlib import asynccontextmanager, closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator


def redact(value: Any) -> Any:
    sensitive = {"password", "token", "secret", "api_key", "authorization"}
    if isinstance(value, dict):
        return {key: "***" if key.lower() in sensitive else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class TraceStore:
    """基于 SQLite 的跨度记录，供 API 检查和评估共同使用。"""

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS spans (
                    id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, parent_id INTEGER,
                    name TEXT NOT NULL, status TEXT NOT NULL, started_at TEXT NOT NULL,
                    duration_ms REAL NOT NULL, attributes TEXT NOT NULL, error TEXT
                );
                CREATE INDEX IF NOT EXISTS ix_spans_run ON spans(run_id, id);
            """)
            db.commit()

    @asynccontextmanager
    async def span(self, run_id: str, name: str, attributes: dict[str, Any] | None = None) -> AsyncIterator[None]:
        started = time.perf_counter()
        status, error = "ok", None
        try:
            yield
        except Exception as exc:
            status, error = "error", f"{type(exc).__name__}: {exc}"
            raise
        finally:
            await asyncio.to_thread(self._write, run_id, name, status, (time.perf_counter() - started) * 1000, attributes or {}, error)

    def _write(self, run_id: str, name: str, status: str, duration_ms: float, attributes: dict[str, Any], error: str | None) -> None:
        with closing(sqlite3.connect(self.path, timeout=10)) as db:
            db.execute(
                "INSERT INTO spans(run_id,name,status,started_at,duration_ms,attributes,error) VALUES(?,?,?,?,?,?,?)",
                (run_id, name, status, datetime.now(timezone.utc).isoformat(), duration_ms,
                 json.dumps(redact(attributes), ensure_ascii=False, default=str), error),
            )
            db.commit()

    async def get_trace(self, run_id: str) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_trace, run_id)

    def _get_trace(self, run_id: str) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.path)) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM spans WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["attributes"] = json.loads(item["attributes"])
            result.append(item)
        return result
