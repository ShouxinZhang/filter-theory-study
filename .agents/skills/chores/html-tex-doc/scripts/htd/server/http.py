"""本地预览、双栏编辑与多论文工作区的 HTTP 服务。"""
from __future__ import annotations

import html
import json
import mimetypes
import re
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .. import assets
from .files import _list_editable_files, _safe_src_file
from .project import PaperLibrary, Project, decode_paper_id
from .search import _search_files

_MIME_MAP = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8", ".mjs": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif",
    ".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf",
}


def _render_live_index(project: Project) -> str:
    base = project.base_url
    base_json = json.dumps(base, ensure_ascii=False)
    paper_json = json.dumps(project.paper_id, ensure_ascii=False).replace("</", "<\\/")
    head_boot = f"<script>window.__HTML_TEX_LIVE__ = true; window.__HTD_BASE__ = {base_json}; window.__HTD_PAPER__ = {paper_json};</script>"
    editor_tag = f'<script defer src="{html.escape(base, quote=True)}__editor.js"></script>'
    idx = project.out_dir / "index.html"
    if idx.exists():
        page = idx.read_text(encoding="utf-8")
        m = re.search(r"<head\b[^>]*>", page, flags=re.I)
        if m:
            page = page[: m.end()] + "\n" + head_boot + page[m.end() :]
        return page.replace("</head>", f"{editor_tag}\n</head>", 1) if "</head>" in page else page
    err_txt = html.escape((project.state.err if project.state else "") or "正在执行首次构建…")
    eb = html.escape(base, quote=True)
    return (
        f"<!DOCTYPE html><html lang='zh-CN'><head>\n{head_boot}\n<meta charset='utf-8'>"
        f"<link rel='stylesheet' href='{eb}style.css'><script defer src='{eb}reader.js'></script>"
        f"{editor_tag}\n</head><body><main id='doc-root' class='doc-pane'><pre>{err_txt}</pre></main></body></html>"
    )


class _HTDServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self, addr: tuple[str, int], handler: type[BaseHTTPRequestHandler],
        project: Project | None = None, library: PaperLibrary | None = None,
        on_close: Callable[[], None] | None = None,
    ):
        super().__init__(addr, handler)
        self.project, self.library, self._on_close = project, library, on_close

    def server_close(self) -> None:
        if self._on_close is not None:
            try:
                self._on_close()
            finally:
                self._on_close = None
        super().server_close()


class _HTDHandler(BaseHTTPRequestHandler):
    server: _HTDServer

    def log_message(self, *args: object) -> None:
        pass

    def _send_bytes(self, body: bytes, ctype: str, status: int = 200, location: str | None = None) -> None:
        try:
            self.send_response(status)
            if location:
                self.send_header("Location", location)
            else:
                self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if body and self.command != "HEAD":
                self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # 注意：mtime_ns 是 19 位整数，超出 JS Number 的精确范围（2^53），一律以字符串收发
    def _send_json(self, obj: object, status: int = 200) -> None:
        self._send_bytes(json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length).decode("utf-8") if length > 0 else "{}")
        if not isinstance(data, dict):
            raise ValueError("JSON 请求体必须为对象")
        return data

    def _serve_static(self, project: Project, sub_path: str) -> None:
        rel = unquote(sub_path).lstrip("/")
        if not rel or "\x00" in rel:
            return self._send_json({"error": "未找到资源"}, HTTPStatus.NOT_FOUND)
        root = project.out_dir.resolve()
        try:
            fp = (root / rel).resolve()
            fp.relative_to(root)
        except (ValueError, OSError):
            return self._send_json({"error": "非法路径"}, HTTPStatus.FORBIDDEN)
        if not fp.is_file():
            if rel in ("style.css", "reader.js"):
                return self._send_bytes(assets.bundle(rel, project.src_dir).encode("utf-8"), _MIME_MAP["." + rel.rsplit(".", 1)[1]])
            return self._send_json({"error": f"文件不存在：{rel}"}, HTTPStatus.NOT_FOUND)
        ctype = _MIME_MAP.get(fp.suffix.lower()) or mimetypes.guess_type(fp.name)[0] or "application/octet-stream"
        self._send_bytes(fp.read_bytes(), ctype)

    def _handle_project_get(self, project: Project, sub_path: str, qs: dict[str, list[str]]) -> None:
        state = project.ensure_started(wait_first=True, timeout=15.0)
        assert project.wal is not None
        if sub_path == "/__live":
            try:
                client_v = int(qs.get("v", ["-1"])[0])
            except ValueError:
                client_v = -1
            with state.cond:
                state.cond.wait_for(lambda: state.v != client_v or state.stopped, timeout=20.0)
                payload = {"v": state.v, "err": state.err, "changed": state.changed}
            return self._send_json(payload)
        if sub_path == "/__raw":
            with state.cond:
                body = state.body_html
            if not body and (project.build_dir / "body.html").exists():
                body = (project.build_dir / "body.html").read_text(encoding="utf-8")
            return self._send_bytes(body.encode("utf-8"), "text/html; charset=utf-8")
        if sub_path == "/__editor.js":
            return self._send_bytes(assets.bundle("editor.js", project.src_dir).encode("utf-8"), "application/javascript; charset=utf-8")
        if sub_path == "/__api/files":
            return self._send_json({"files": _list_editable_files(project.src_dir)})
        if sub_path == "/__api/file":
            rel = qs.get("path", [""])[0]
            fp = _safe_src_file(project.src_dir, rel)
            if not fp or not fp.is_file():
                return self._send_json({"error": f"文件不存在或禁止访问：{rel}"}, HTTPStatus.NOT_FOUND)
            st = fp.stat()
            return self._send_json({"path": rel, "content": fp.read_text(encoding="utf-8", errors="replace"), "mtime_ns": str(st.st_mtime_ns)})
        if sub_path == "/__api/search":
            return self._send_json(_search_files(project.src_dir, qs.get("q", [""])[0], qs.get("case", ["0"])[0] == "1", qs.get("regex", ["0"])[0] == "1"))
        if sub_path == "/__api/history":
            rel = qs.get("path", [""])[0]
            if not _safe_src_file(project.src_dir, rel):
                return self._send_json({"error": "非法路径"}, HTTPStatus.BAD_REQUEST)
            return self._send_json({"path": rel, "ops": project.wal.list_ops(rel)})
        if sub_path in ("/", "/index.html"):
            return self._send_bytes(_render_live_index(project).encode("utf-8"), "text/html; charset=utf-8")
        self._serve_static(project, sub_path)

    def _handle_project_put(self, project: Project, sub_path: str, qs: dict[str, list[str]]) -> None:
        if sub_path != "/__api/file":
            return self._send_json({"error": "未知接口"}, HTTPStatus.NOT_FOUND)
        try:
            req = self._read_json()
            content = str(req["content"])
            rel = qs.get("path", [""])[0] or str(req.get("path", ""))
        except Exception as e:
            return self._send_json({"error": f"请求格式错误：{e}"}, HTTPStatus.BAD_REQUEST)
        status, payload = project.save_file(rel, content, req.get("base_mtime_ns"), bool(req.get("force", False)))
        self._send_json(payload, status)

    def _handle_project_post(self, project: Project, sub_path: str) -> None:
        if sub_path != "/__api/rollback":
            return self._send_json({"error": "未知接口"}, HTTPStatus.NOT_FOUND)
        try:
            req = self._read_json()
            rel, op_id = str(req["path"]), int(str(req["id"]))
        except Exception as e:
            return self._send_json({"error": f"请求格式错误：{e}"}, HTTPStatus.BAD_REQUEST)
        status, payload = project.rollback_file(rel, op_id)
        self._send_json(payload, status)

    def _resolve_library_subroute(self, path: str) -> tuple[Project | None, str]:
        if not path.startswith("/p/") or "/" not in path[3:]:
            return None, ""
        slug, tail = path[3:].split("/", 1)
        assert self.server.library is not None
        return self.server.library.get_by_slug(slug), "/" + tail

    def do_GET(self) -> None:
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        if self.server.library is None:
            assert self.server.project is not None
            return self._handle_project_get(self.server.project, u.path, qs)
        lib = self.server.library
        if u.path in ("/", "/index.html"):
            return self._send_bytes(assets.render_shell_html().encode("utf-8"), "text/html; charset=utf-8")
        if u.path == "/__shell.css":
            return self._send_bytes(assets.bundle("shell.css").encode("utf-8"), "text/css; charset=utf-8")
        if u.path == "/__shell.js":
            return self._send_bytes(assets.bundle("shell.js").encode("utf-8"), "application/javascript; charset=utf-8")
        if u.path == "/__api/papers":
            return self._send_json({"library": lib.root.name, "papers": lib.list_papers()})
        if u.path.startswith("/p/") and "/" not in u.path[3:]:
            slug = u.path[3:]
            if decode_paper_id(slug) is None:
                return self._send_json({"error": "非法论文标识"}, HTTPStatus.NOT_FOUND)
            loc = f"/p/{slug}/" + (f"?{u.query}" if u.query else "")
            return self._send_bytes(b"", "", HTTPStatus.FOUND, location=loc)
        proj, sub = self._resolve_library_subroute(u.path)
        if proj is None:
            return self._send_json({"error": "未找到对应论文或路径"}, HTTPStatus.NOT_FOUND)
        self._handle_project_get(proj, sub, qs)

    do_HEAD = do_GET

    def do_PUT(self) -> None:
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        if self.server.library is None:
            assert self.server.project is not None
            return self._handle_project_put(self.server.project, u.path, qs)
        proj, sub = self._resolve_library_subroute(u.path)
        if proj is None:
            return self._send_json({"error": "未找到对应论文"}, HTTPStatus.NOT_FOUND)
        self._handle_project_put(proj, sub, qs)

    def do_POST(self) -> None:
        u = urlparse(self.path)
        if self.server.library is None:
            assert self.server.project is not None
            return self._handle_project_post(self.server.project, u.path)
        if u.path == "/__api/papers":
            try:
                req = self._read_json()
                name, title = req.get("name"), req.get("title")
                preset = str(req.get("preset") or "academic-md")
                if not isinstance(name, str) or (title is not None and not isinstance(title, str)):
                    raise ValueError("name/title 类型错误")
                paper = self.server.library.create_paper(name=name, title=title, preset=preset)
            except FileExistsError as e:
                return self._send_json({"error": str(e)}, HTTPStatus.CONFLICT)
            except (ValueError, OSError) as e:
                return self._send_json({"error": str(e)}, HTTPStatus.BAD_REQUEST)
            return self._send_json({"ok": True, "paper": paper}, HTTPStatus.CREATED)
        proj, sub = self._resolve_library_subroute(u.path)
        if proj is None:
            return self._send_json({"error": "未找到对应论文"}, HTTPStatus.NOT_FOUND)
        self._handle_project_post(proj, sub)


def make_single_server(
    src_dir: Path, build_dir: Path, out_dir: Path, host: str = "127.0.0.1", port: int = 18767, force_first: bool = False,
) -> _HTDServer:
    proj = Project(src_dir, build_dir, out_dir, paper_id="", base_url="/", force_first=force_first)
    proj.ensure_started(wait_first=True, timeout=15.0)
    return _HTDServer((host, port), _HTDHandler, project=proj, on_close=proj.close)


def make_library_server(library_root: Path, host: str = "127.0.0.1", port: int = 18767, force_first: bool = False) -> _HTDServer:
    lib = PaperLibrary(library_root, force_first=force_first)
    return _HTDServer((host, port), _HTDHandler, library=lib, on_close=lib.close)


def _serve_forever(srv: _HTDServer) -> int:
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


def run_server(
    src_dir: Path, build_dir: Path, out_dir: Path, host: str = "127.0.0.1", port: int = 18767, force_first: bool = False,
) -> int:
    srv = make_single_server(src_dir, build_dir, out_dir, host=host, port=port, force_first=force_first)
    print(f"实时工作台已就绪：http://{host}:{srv.server_address[1]}/", flush=True)
    print(f"源码目录：{src_dir.resolve()}  （Ctrl+\\ 切换双栏，Ctrl+单击 正反向高亮对齐；Ctrl+C 退出）", flush=True)
    return _serve_forever(srv)


def run_library_server(library_root: Path, host: str = "127.0.0.1", port: int = 18767, force_first: bool = False) -> int:
    srv = make_library_server(library_root, host=host, port=port, force_first=force_first)
    print(f"多论文工作区已就绪：http://{host}:{srv.server_address[1]}/", flush=True)
    print(f"论文库根目录：{library_root.resolve()}  （按需惰性构建；Ctrl+C 退出）", flush=True)
    return _serve_forever(srv)
