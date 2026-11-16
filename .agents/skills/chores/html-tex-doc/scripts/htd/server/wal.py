"""编辑增量日志（SQLite）与回滚。"""
from __future__ import annotations

import difflib
import json
import sqlite3
import threading
import time
from pathlib import Path

class _EditWAL:
    """基于 SQLite + difflib 的增量差量事务日志，仅记录每次 update 的变更 hunk。"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS edit_ops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    path TEXT NOT NULL,
                    source TEXT NOT NULL,
                    ops_json TEXT NOT NULL,
                    summary TEXT NOT NULL
                )"""
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_edit_ops_path_id ON edit_ops(path, id DESC)")

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=5.0)

    def record_delta(self, rel: str, old_txt: str, new_txt: str, source: str = "web") -> int | None:
        if old_txt == new_txt:
            return None
        old_lines = old_txt.splitlines(keepends=True)
        new_lines = new_txt.splitlines(keepends=True)
        sm = difflib.SequenceMatcher(None, new_lines, old_lines)
        ops: list[list[object]] = []
        added = deleted = 0
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            added += i2 - i1
            deleted += j2 - j1
            ops.append([tag, i1, i2, old_lines[j1:j2]])
        if not ops:
            return None
        summary = f"+{added} / -{deleted} 行"
        with self.lock, self._conn() as c:
            cur = c.execute(
                "INSERT INTO edit_ops(ts, path, source, ops_json, summary) VALUES (?, ?, ?, ?, ?)",
                (time.time(), rel, source, json.dumps(ops, ensure_ascii=False), summary),
            )
            return cur.lastrowid

    def list_ops(self, rel: str, limit: int = 30) -> list[dict[str, object]]:
        with self.lock, self._conn() as c:
            rows = c.execute(
                "SELECT id, ts, source, summary FROM edit_ops WHERE path = ? ORDER BY id DESC LIMIT ?",
                (rel, limit),
            ).fetchall()
        return [{"id": r[0], "ts": r[1], "source": r[2], "summary": r[3]} for r in rows]

    def rollback_to(self, rel: str, op_id: int, cur_txt: str) -> str | None:
        with self.lock, self._conn() as c:
            rows = c.execute(
                "SELECT ops_json FROM edit_ops WHERE path = ? AND id >= ? ORDER BY id DESC",
                (rel, op_id),
            ).fetchall()
        if not rows:
            return None
        lines = cur_txt.splitlines(keepends=True)
        for (ops_raw,) in rows:
            ops = json.loads(ops_raw)
            for _tag, i1, i2, old_slice in reversed(ops):
                lines[i1:i2] = old_slice
        return "".join(lines)
