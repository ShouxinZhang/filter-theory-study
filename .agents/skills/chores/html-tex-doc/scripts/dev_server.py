#!/usr/bin/env python3
"""本地实时预览与 Web 双栏编辑服务器（供 html_tex_doc.py serve 调用）。

绑定 127.0.0.1，提供：
- GET  / 或 /index.html    注入 /__editor.js 的工作台页面
- GET  /__editor.js        双栏编辑器、搜索与类 SyncTeX 正反向高亮对齐脚本
- GET  /__live?v=<int>     长轮询构建版本号、错误与变更文件列表
- GET  /__raw              最新一次成功构建的 #doc-root 纯净内部 HTML
- GET  /__api/files        可编辑源文件清单与 mtime_ns
- GET  /__api/file?path=   读取单个源文件文本与 mtime_ns
- PUT  /__api/file?path=   带 mtime_ns 乐观锁校验写回源文件并即时唤醒增量构建
- GET  /__api/search?q=    跨全部源文件的全文/正则搜索接口
"""
from __future__ import annotations

import difflib
import json
import re
import sqlite3
import threading
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from html_tex_doc import TEMPLATE_BASIC, _resolve_asset, build_project

EDITABLE_EXTS = {".md", ".tex", ".bib", ".html", ".css"}
SKIP_NAMES = {"reader.js", "editor.js"}


def _safe_src_file(src_dir: Path, rel: str) -> Path | None:
    if not rel or "\x00" in rel:
        return None
    root = src_dir.resolve()
    try:
        target = (root / rel).resolve()
        target.relative_to(root)
    except (ValueError, OSError):
        return None
    if target.name in SKIP_NAMES or target.suffix.lower() not in EDITABLE_EXTS:
        return None
    return target


def _list_editable_files(src_dir: Path) -> list[dict[str, object]]:
    root = src_dir.resolve()
    items: list[tuple[tuple[int, str], dict[str, object]]] = []
    for p in root.rglob("*"):
        if not p.is_file() or p.name.startswith(".") or p.name in SKIP_NAMES:
            continue
        if p.suffix.lower() not in EDITABLE_EXTS:
            continue
        rel = p.relative_to(root).as_posix()
        if rel == "style.css":
            grp = 4
        elif p.suffix == ".md":
            grp = 0
        elif rel == "doc.html":
            grp = 1
        elif rel in ("macros.tex", "refs.bib"):
            grp = 2
        else:
            grp = 3
        try:
            st = p.stat()
        except OSError:
            continue
        items.append(((grp, rel), {"path": rel, "size": st.st_size, "mtime_ns": st.st_mtime_ns}))
    items.sort(key=lambda x: x[0])
    return [x[1] for x in items]


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


class LiveState:
    def __init__(self, src_dir: Path, build_dir: Path, out_dir: Path):
        self.src_dir = src_dir.resolve()
        self.build_dir = build_dir.resolve()
        self.out_dir = out_dir.resolve()
        self.cond = threading.Condition()
        self.wakeup = threading.Event()
        self.v = 0
        self.err = ""
        self.body_html = ""
        self.changed: list[str] = []

    def snapshot_mtimes(self) -> dict[str, int]:
        out: dict[str, int] = {}
        try:
            for p in self.src_dir.rglob("*"):
                if p.is_file() and not p.name.startswith("."):
                    rel = p.relative_to(self.src_dir).as_posix()
                    out[rel] = p.stat().st_mtime_ns
        except OSError:
            pass
        return out


def _watch_loop(state: LiveState, force_first: bool) -> None:
    prev: dict[str, int] | None = None
    first = True
    while True:
        cur = state.snapshot_mtimes()
        if prev is None or cur != prev:
            changed = [] if prev is None else sorted(k for k, v in cur.items() if prev.get(k) != v)
            prev = cur
            t0 = time.time()
            try:
                rc, msg, body = build_project(
                    state.src_dir,
                    state.build_dir,
                    state.out_dir,
                    force=(force_first and first),
                )
                first = False
                err = msg if rc != 0 else ""
            except Exception as e:
                rc, err, body = 1, f"{type(e).__name__}: {e}", ""
            with state.cond:
                state.v += 1
                state.err = err
                if rc == 0:
                    state.body_html = body
                state.changed = changed
                state.cond.notify_all()
            dt = (time.time() - t0) * 1000
            stamp = time.strftime("%H:%M:%S")
            if err:
                print(f"[{stamp}] 构建失败（{dt:.0f} ms）\n{err}", flush=True)
            else:
                ch_info = f" [{', '.join(changed[:3])}]" if changed else ""
                print(f"[{stamp}] 已刷新 v={state.v}（{dt:.0f} ms）{ch_info}", flush=True)
        state.wakeup.wait(timeout=0.25)
        state.wakeup.clear()


def _search_files(src_dir: Path, query: str, case_sensitive: bool, use_regex: bool, limit: int = 400) -> dict[str, object]:
    if not query:
        return {"hits": [], "truncated": False}
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        pat = re.compile(query if use_regex else re.escape(query), flags)
    except re.error as e:
        return {"error": f"无效正则表达式：{e}", "hits": [], "truncated": False}

    hits: list[dict[str, object]] = []
    truncated = False
    for meta in _list_editable_files(src_dir):
        rel = str(meta["path"])
        fp = src_dir / rel
        try:
            lines = fp.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for idx, line in enumerate(lines):
            for m in pat.finditer(line):
                col = m.start()
                mlen = m.end() - m.start()
                if mlen == 0:
                    continue
                s0 = max(0, col - 36)
                s1 = min(len(line), m.end() + 64)
                prefix = ("…" if s0 > 0 else "") + line[s0:col]
                match_txt = line[col : m.end()]
                suffix = line[m.end() : s1] + ("…" if s1 < len(line) else "")
                hits.append(
                    {
                        "path": rel,
                        "line": idx + 1,
                        "col": col,
                        "len": mlen,
                        "before": prefix,
                        "match": match_txt,
                        "after": suffix,
                    }
                )
                if len(hits) >= limit:
                    truncated = True
                    break
            if truncated:
                break
        if truncated:
            break
    return {"hits": hits, "truncated": truncated}


def run_server(
    src_dir: Path,
    build_dir: Path,
    out_dir: Path,
    host: str = "127.0.0.1",
    port: int = 18767,
    force_first: bool = False,
) -> int:
    src_dir, build_dir, out_dir = src_dir.resolve(), build_dir.resolve(), out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    wal = _EditWAL(build_dir / "edits.db")
    state = LiveState(src_dir, build_dir, out_dir)
    threading.Thread(target=_watch_loop, args=(state, force_first), daemon=True).start()

    # 等待首轮构建完成（最长 15s），避免首次打开空白
    with state.cond:
        state.cond.wait_for(lambda: state.v >= 1, timeout=15.0)

    class DevHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

        def _send_bytes(self, body: bytes, ctype: str, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, obj: object, status: int = 200) -> None:
            self._send_bytes(json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-cache")
            super().end_headers()

        def do_GET(self) -> None:
            u = urlparse(self.path)
            qs = parse_qs(u.query)

            if u.path == "/__live":
                try:
                    client_v = int(qs.get("v", ["-1"])[0])
                except ValueError:
                    client_v = -1
                with state.cond:
                    state.cond.wait_for(lambda: state.v != client_v, timeout=20.0)
                    payload = {"v": state.v, "err": state.err, "changed": state.changed}
                return self._send_json(payload)

            if u.path == "/__raw":
                with state.cond:
                    body = state.body_html
                if not body and (build_dir / "body.html").exists():
                    body = (build_dir / "body.html").read_text(encoding="utf-8")
                return self._send_bytes(body.encode("utf-8"), "text/html; charset=utf-8")

            if u.path == "/__editor.js":
                ed = _resolve_asset(src_dir, "editor.js")
                if not ed.exists():
                    ed = TEMPLATE_BASIC / "editor.js"
                js = ed.read_text(encoding="utf-8") if ed.exists() else ""
                return self._send_bytes(js.encode("utf-8"), "application/javascript; charset=utf-8")

            if u.path == "/__api/files":
                return self._send_json({"files": _list_editable_files(src_dir)})

            if u.path == "/__api/file":
                rel = qs.get("path", [""])[0]
                fp = _safe_src_file(src_dir, rel)
                if not fp or not fp.is_file():
                    return self._send_json({"error": f"文件不存在或禁止访问：{rel}"}, HTTPStatus.NOT_FOUND)
                st = fp.stat()
                txt = fp.read_text(encoding="utf-8", errors="replace")
                return self._send_json({"path": rel, "content": txt, "mtime_ns": st.st_mtime_ns})

            if u.path == "/__api/search":
                q = qs.get("q", [""])[0]
                cs = qs.get("case", ["0"])[0] == "1"
                rx = qs.get("regex", ["0"])[0] == "1"
                return self._send_json(_search_files(src_dir, q, cs, rx))

            if u.path == "/__api/history":
                rel = qs.get("path", [""])[0]
                fp = _safe_src_file(src_dir, rel)
                if not fp:
                    return self._send_json({"error": "非法路径"}, HTTPStatus.BAD_REQUEST)
                return self._send_json({"path": rel, "ops": wal.list_ops(rel)})

            if u.path in ("/", "/index.html"):
                idx = out_dir / "index.html"
                if idx.exists():
                    page = idx.read_text(encoding="utf-8")
                    inject = '<script>window.__HTML_TEX_LIVE__ = true;</script>\n<script defer src="/__editor.js"></script>\n</head>'
                    page = page.replace("</head>", inject, 1)
                else:
                    err_html = state.err or "正在执行首次构建…"
                    page = (
                        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
                        "<link rel='stylesheet' href='style.css'>"
                        "<script>window.__HTML_TEX_LIVE__ = true;</script>"
                        "<script defer src='reader.js'></script>"
                        "<script defer src='/__editor.js'></script></head>"
                        f"<body><main id='doc-root' class='doc-pane'><pre>{err_html}</pre></main></body></html>"
                    )
                return self._send_bytes(page.encode("utf-8"), "text/html; charset=utf-8")

            super().do_GET()

        def do_PUT(self) -> None:
            u = urlparse(self.path)
            qs = parse_qs(u.query)
            if u.path != "/__api/file":
                return self._send_json({"error": "未知接口"}, HTTPStatus.NOT_FOUND)

            try:
                length = int(self.headers.get("Content-Length", "0"))
                req = json.loads(self.rfile.read(length).decode("utf-8"))
                content = str(req["content"])
                base_mtime = req.get("base_mtime_ns")
                force = bool(req.get("force", False))
            except Exception as e:
                return self._send_json({"error": f"请求格式错误：{e}"}, HTTPStatus.BAD_REQUEST)

            rel = qs.get("path", [""])[0] or str(req.get("path", ""))
            fp = _safe_src_file(src_dir, rel)
            if not fp or not fp.exists():
                return self._send_json({"error": f"文件不存在或禁止写入：{rel}"}, HTTPStatus.NOT_FOUND)

            st = fp.stat()
            if base_mtime is not None and not force and int(base_mtime) != st.st_mtime_ns:
                disk_txt = fp.read_text(encoding="utf-8", errors="replace")
                if disk_txt != content:
                    return self._send_json(
                        {
                            "ok": False,
                            "conflict": True,
                            "mtime_ns": st.st_mtime_ns,
                            "disk_content": disk_txt,
                        },
                        HTTPStatus.CONFLICT,
                    )

            old_txt = fp.read_text(encoding="utf-8", errors="replace")
            if old_txt != content:
                wal.record_delta(rel, old_txt, content, source="web")

            fp.write_text(content, encoding="utf-8")
            new_mtime = fp.stat().st_mtime_ns
            state.wakeup.set()
            return self._send_json({"ok": True, "path": rel, "mtime_ns": new_mtime})

        def do_POST(self) -> None:
            u = urlparse(self.path)
            if u.path != "/__api/rollback":
                return self._send_json({"error": "未知接口"}, HTTPStatus.NOT_FOUND)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                req = json.loads(self.rfile.read(length).decode("utf-8"))
                rel = str(req["path"])
                op_id = int(req["id"])
            except Exception as e:
                return self._send_json({"error": f"请求格式错误：{e}"}, HTTPStatus.BAD_REQUEST)
            fp = _safe_src_file(src_dir, rel)
            if not fp or not fp.is_file():
                return self._send_json({"error": f"文件不存在：{rel}"}, HTTPStatus.NOT_FOUND)
            cur_txt = fp.read_text(encoding="utf-8", errors="replace")
            restored = wal.rollback_to(rel, op_id, cur_txt)
            if restored is None:
                return self._send_json({"error": "未找到对应增量记录"}, HTTPStatus.NOT_FOUND)
            wal.record_delta(rel, cur_txt, restored, source="rollback")
            fp.write_text(restored, encoding="utf-8")
            new_mtime = fp.stat().st_mtime_ns
            state.wakeup.set()
            return self._send_json({"ok": True, "path": rel, "content": restored, "mtime_ns": new_mtime})

    srv = ThreadingHTTPServer((host, port), lambda *a: DevHandler(*a, directory=str(out_dir)))
    srv.daemon_threads = True
    print(f"实时工作台已就绪：http://{host}:{port}/", flush=True)
    print(f"源码目录：{src_dir}  （Ctrl+\\ 切换双栏，Ctrl+单击 正反向高亮对齐；Ctrl+C 退出）", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0
