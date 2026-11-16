"""本地预览与双栏编辑的 HTTP 服务。"""
from __future__ import annotations

import json
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ..assets import bundle
from .files import _list_editable_files, _safe_src_file
from .search import _search_files
from .wal import _EditWAL
from .watch import LiveState, _watch_loop

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

        # 注意：mtime_ns 是 19 位整数，超出 JS Number 的精确范围（2^53），一律以字符串收发
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
                js = bundle("editor.js", src_dir)
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
                return self._send_json({"path": rel, "content": txt, "mtime_ns": str(st.st_mtime_ns)})

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
            if base_mtime is not None and not force and str(base_mtime) != str(st.st_mtime_ns):
                disk_txt = fp.read_text(encoding="utf-8", errors="replace")
                if disk_txt != content:
                    return self._send_json(
                        {
                            "ok": False,
                            "conflict": True,
                            "mtime_ns": str(st.st_mtime_ns),
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
            return self._send_json({"ok": True, "path": rel, "mtime_ns": str(new_mtime)})

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
            return self._send_json({"ok": True, "path": rel, "content": restored, "mtime_ns": str(new_mtime)})

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
