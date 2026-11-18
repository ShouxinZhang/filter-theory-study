"""单工程运行态封装、骨架初始化与多论文库惰性管理。"""
from __future__ import annotations

import html
import os
import re
import shutil
import threading
from http import HTTPStatus
from pathlib import Path
from urllib.parse import quote, unquote

from ..paths import TEMPLATE_ACADEMIC, TEMPLATE_BASIC
from ..workspace import discover_papers, read_paper_meta
from .files import _safe_src_file
from .wal import _EditWAL
from .watch import LiveState, _watch_loop

_SKIP_DIRS = {"build", "outputs", "src", "node_modules", "__pycache__", "public-references"}


def encode_paper_id(paper_id: str) -> str:
    return quote(paper_id.replace("~", "~~").replace("/", "~"), safe="-_.~")


def decode_paper_id(slug: str) -> str | None:
    if not slug:
        return None
    raw = unquote(slug)
    if not raw or "\x00" in raw or "\\" in raw or "/" in raw:
        return None
    paper_id = raw.replace("~~", "\x00").replace("~", "/").replace("\x00", "~")
    if not paper_id or paper_id.startswith("/") or ".." in paper_id:
        return None
    if any(seg in ("", ".") for seg in paper_id.split("/")):
        return None
    return paper_id


def _write_text_monotonic(fp: Path, content: str, prev_mtime_ns: int) -> int:
    fp.write_text(content, encoding="utf-8")
    st = fp.stat()
    if st.st_mtime_ns <= prev_mtime_ns:
        os.utime(fp, ns=(st.st_atime_ns, prev_mtime_ns + 1))
        st = fp.stat()
    return st.st_mtime_ns


def init_project(project_dir: Path, title: str | None = None, preset: str = "basic", force: bool = False) -> Path:
    if preset not in ("basic", "academic-md"):
        raise ValueError(f"不支持的预设模板：{preset}")
    tpl = TEMPLATE_ACADEMIC if preset == "academic-md" else TEMPLATE_BASIC
    if not tpl.exists():
        raise FileNotFoundError(f"找不到预设模板目录：{tpl}")
    dest = project_dir.resolve() / "src"
    if dest.exists() and any(dest.iterdir()) and not force:
        raise FileExistsError(f"目标已存在且非空：{dest}（如需覆盖请加 --force）")
    if dest.exists() and force:
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(tpl, dest)
    if not (dest / "common.tex").exists() and (TEMPLATE_BASIC / "common.tex").exists():
        shutil.copy(TEMPLATE_BASIC / "common.tex", dest / "common.tex")
    clean = (title or "").replace("\r", " ").replace("\n", " ").strip()
    if clean:
        for candidate in (dest / "main.md", dest / "doc.html", dest / "00_摘要.md", dest / "01_正文.md"):
            if candidate.exists():
                txt = candidate.read_text(encoding="utf-8")
                if candidate.name == "main.md":
                    txt = re.sub(r"^title:\s*['\"]?文档标题['\"]?[ \t]*$", lambda _: f"title: {clean}", txt, count=1, flags=re.M)
                txt = txt.replace("<!-- title: 文档标题 -->", f"<!-- title: {clean} -->", 1)
                txt = txt.replace("<h1>文档标题</h1>", f"<h1>{html.escape(clean)}</h1>", 1)
                candidate.write_text(txt, encoding="utf-8")
    return dest


class Project:
    def __init__(
        self, src_dir: Path, build_dir: Path, out_dir: Path,
        paper_id: str = "", base_url: str = "/", force_first: bool = False,
    ):
        self.paper_id = paper_id
        self.slug = encode_paper_id(paper_id) if paper_id else ""
        self.base_url = base_url if base_url.endswith("/") else base_url + "/"
        self.src_dir, self.build_dir, self.out_dir = src_dir.resolve(), build_dir.resolve(), out_dir.resolve()
        self.force_first = force_first
        self.file_lock = threading.Lock()
        self._start_lock = threading.Lock()
        self.wal: _EditWAL | None = None
        self.state: LiveState | None = None
        self._stop_event: threading.Event | None = None
        self._thread: threading.Thread | None = None

    @property
    def alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive() and not (self._stop_event and self._stop_event.is_set()))

    def ensure_started(self, wait_first: bool = True, timeout: float = 15.0) -> LiveState:
        with self._start_lock:
            if not self.alive:
                self.out_dir.mkdir(parents=True, exist_ok=True)
                if self.wal is None:
                    self.wal = _EditWAL(self.build_dir / "edits.db")
                stop_ev = threading.Event()
                state = LiveState(self.src_dir, self.build_dir, self.out_dir)
                t = threading.Thread(target=_watch_loop, args=(state, self.force_first, stop_ev, self.paper_id), daemon=True)
                self._stop_event, self.state, self._thread = stop_ev, state, t
                t.start()
            state = self.state
        assert state is not None
        if wait_first:
            with state.cond:
                state.cond.wait_for(lambda: state.v >= 1 or state.stopped, timeout=timeout)
        return state

    def save_file(self, rel: str, content: str, base_mtime: object = None, force: bool = False) -> tuple[int, dict[str, object]]:
        state = self.ensure_started(wait_first=True, timeout=15.0)
        assert self.wal is not None
        fp = _safe_src_file(self.src_dir, rel)
        if not fp or not fp.exists():
            return HTTPStatus.NOT_FOUND, {"error": f"文件不存在或禁止写入：{rel}"}
        with self.file_lock:
            st = fp.stat()
            if base_mtime is not None and not force and str(base_mtime) != str(st.st_mtime_ns):
                disk_txt = fp.read_text(encoding="utf-8", errors="replace")
                if disk_txt != content:
                    return HTTPStatus.CONFLICT, {
                        "ok": False, "conflict": True, "mtime_ns": str(st.st_mtime_ns), "disk_content": disk_txt,
                    }
            old_txt = fp.read_text(encoding="utf-8", errors="replace")
            if old_txt != content:
                self.wal.record_delta(rel, old_txt, content, source="web")
            new_mtime = _write_text_monotonic(fp, content, st.st_mtime_ns)
        state.wakeup.set()
        return HTTPStatus.OK, {"ok": True, "path": rel, "mtime_ns": str(new_mtime)}

    def rollback_file(self, rel: str, op_id: int) -> tuple[int, dict[str, object]]:
        state = self.ensure_started(wait_first=True, timeout=15.0)
        assert self.wal is not None
        fp = _safe_src_file(self.src_dir, rel)
        if not fp or not fp.is_file():
            return HTTPStatus.NOT_FOUND, {"error": f"文件不存在：{rel}"}
        with self.file_lock:
            st = fp.stat()
            cur_txt = fp.read_text(encoding="utf-8", errors="replace")
            restored = self.wal.rollback_to(rel, op_id, cur_txt)
            if restored is None:
                return HTTPStatus.NOT_FOUND, {"error": "未找到对应增量记录"}
            self.wal.record_delta(rel, cur_txt, restored, source="rollback")
            new_mtime = _write_text_monotonic(fp, restored, st.st_mtime_ns)
        state.wakeup.set()
        return HTTPStatus.OK, {"ok": True, "path": rel, "content": restored, "mtime_ns": str(new_mtime)}

    def close(self, join_timeout: float = 2.0) -> None:
        with self._start_lock:
            stop_ev, state, t = self._stop_event, self.state, self._thread
            self._thread = None
        if stop_ev is not None:
            stop_ev.set()
        if state is not None:
            state.wakeup.set()
            with state.cond:
                state.stopped = True
                state.cond.notify_all()
        if t is not None and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=join_timeout)


class PaperLibrary:
    def __init__(self, library_root: Path, force_first: bool = False, max_depth: int = 2):
        self.root = library_root.resolve()
        self.force_first = force_first
        self.max_depth = max_depth
        self._lock = threading.Lock()
        self.projects: dict[str, Project] = {}

    def _new_project(self, paper_id: str, proj_dir: Path) -> Project:
        slug = encode_paper_id(paper_id)
        return Project(
            proj_dir / "src", proj_dir / "build", proj_dir / "outputs" / "site",
            paper_id=paper_id, base_url=f"/p/{slug}/", force_first=self.force_first,
        )

    def list_papers(self) -> list[dict[str, object]]:
        items = discover_papers(self.root, max_depth=self.max_depth) if self.root.is_dir() else []
        valid_ids = {it["id"] for it in items}
        with self._lock:
            stale = [self.projects.pop(pid) for pid in list(self.projects) if pid not in valid_ids]
            out: list[dict[str, object]] = []
            for it in items:
                pid = it["id"]
                proj = self.projects.get(pid)
                if proj is None:
                    proj = self._new_project(pid, self.root / pid)
                    self.projects[pid] = proj
                out.append({
                    "id": pid, "slug": proj.slug, "url": proj.base_url,
                    "title": it["title"], "entry": it["entry"], "alive": proj.alive,
                })
        for p in stale:
            p.close()
        return out

    def get_project(self, paper_id: str) -> Project | None:
        try:
            proj_dir = (self.root / paper_id).resolve()
            rel = proj_dir.relative_to(self.root)
        except (ValueError, OSError):
            return None
        if not (1 <= len(rel.parts) <= self.max_depth) or any(p.startswith(".") or p in _SKIP_DIRS for p in rel.parts):
            return None
        src_dir = proj_dir / "src"
        if not src_dir.is_dir() or read_paper_meta(src_dir).entry is None:
            with self._lock:
                old = self.projects.pop(paper_id, None)
            if old is not None:
                old.close()
            return None
        with self._lock:
            proj = self.projects.get(paper_id)
            if proj is None:
                proj = self._new_project(paper_id, proj_dir)
                self.projects[paper_id] = proj
            return proj

    def get_by_slug(self, slug: str) -> Project | None:
        pid = decode_paper_id(slug)
        return self.get_project(pid) if pid is not None else None

    def create_paper(self, name: str, title: str | None = None, preset: str = "academic-md") -> dict[str, object]:
        if not isinstance(name, str):
            raise ValueError("论文名称必须为字符串")
        name = name.strip()
        if not name or any(x in name for x in ("/", "\\", "..", "\x00")) or name.startswith(".") or name in _SKIP_DIRS:
            raise ValueError(f"非法的论文目录名：{name!r}")
        preset = preset or "academic-md"
        if preset not in ("basic", "academic-md"):
            raise ValueError(f"不支持的预设模板：{preset}")
        eff_title = title.strip() if isinstance(title, str) and title.strip() else name
        with self._lock:
            self.root.mkdir(parents=True, exist_ok=True)
            proj_dir = (self.root / name).resolve()
            if proj_dir.parent != self.root:
                raise ValueError(f"非法的论文目录名：{name!r}")
            if proj_dir.exists():
                raise FileExistsError(f"论文目录已存在：{name}")
            init_project(proj_dir, title=eff_title, preset=preset, force=False)
            proj = self._new_project(name, proj_dir)
            self.projects[name] = proj
        proj.ensure_started(wait_first=True, timeout=10.0)
        meta = read_paper_meta(proj.src_dir)
        return {
            "id": name, "slug": proj.slug, "url": proj.base_url,
            "title": meta.title or eff_title, "entry": meta.entry, "alive": proj.alive,
        }

    def close(self) -> None:
        with self._lock:
            projs = list(self.projects.values())
            self.projects.clear()
        for p in projs:
            p.close()
