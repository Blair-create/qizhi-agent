from __future__ import annotations

import asyncio
import json
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class MemoryItem:
    id: int
    kind: str
    content: str
    metadata: dict[str, Any]
    score: float = 0.0


class SQLiteMemoryStore:
    """持久化短期消息和可搜索的用户记忆。"""

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY, thread_id TEXT NOT NULL, role TEXT NOT NULL,
                    content TEXT NOT NULL, run_id TEXT, created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_messages_thread ON messages(thread_id, id);
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, kind TEXT NOT NULL,
                    content TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL, UNIQUE(user_id, kind, content)
                );
                CREATE INDEX IF NOT EXISTS ix_memories_user ON memories(user_id, id);
            """)

    async def append_message(self, thread_id: str, role: str, content: str, run_id: str) -> None:
        await asyncio.to_thread(self._append_message, thread_id, role, content, run_id)

    def _append_message(self, thread_id: str, role: str, content: str, run_id: str) -> None:
        with closing(self._connect()) as db:
            db.execute("INSERT INTO messages(thread_id, role, content, run_id, created_at) VALUES(?,?,?,?,?)",
                       (thread_id, role, content, run_id, datetime.now(timezone.utc).isoformat()))
            db.commit()

    async def recent_messages(self, thread_id: str, limit: int = 12) -> list[dict[str, str]]:
        return await asyncio.to_thread(self._recent_messages, thread_id, limit)

    def _recent_messages(self, thread_id: str, limit: int) -> list[dict[str, str]]:
        with closing(self._connect()) as db:
            rows = db.execute("SELECT role, content FROM messages WHERE thread_id=? ORDER BY id DESC LIMIT ?",
                              (thread_id, limit)).fetchall()
        return [dict(row) for row in reversed(rows)]

    async def remember(self, user_id: str, kind: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        await asyncio.to_thread(self._remember, user_id, kind, content, metadata or {})

    def _remember(self, user_id: str, kind: str, content: str, metadata: dict[str, Any]) -> None:
        with closing(self._connect()) as db:
            db.execute("INSERT OR IGNORE INTO memories(user_id, kind, content, metadata, created_at) VALUES(?,?,?,?,?)",
                       (user_id, kind, content, json.dumps(metadata, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))
            db.commit()

    async def recall(self, user_id: str, query: str, limit: int = 5) -> list[MemoryItem]:
        return await asyncio.to_thread(self._recall, user_id, query, limit)

    def _recall(self, user_id: str, query: str, limit: int) -> list[MemoryItem]:
        terms = set(re.findall(r"[\w\u4e00-\u9fff]+", query.lower()))
        with closing(self._connect()) as db:
            rows = db.execute("SELECT id, kind, content, metadata FROM memories WHERE user_id=? ORDER BY id DESC LIMIT 200",
                              (user_id,)).fetchall()
        items: list[MemoryItem] = []
        for row in rows:
            text_terms = set(re.findall(r"[\w\u4e00-\u9fff]+", row["content"].lower()))
            score = len(terms & text_terms) / max(len(terms), 1)
            if score > 0 or not terms:
                items.append(MemoryItem(row["id"], row["kind"], row["content"], json.loads(row["metadata"]), score))
        return sorted(items, key=lambda item: (item.score, item.id), reverse=True)[:limit]
