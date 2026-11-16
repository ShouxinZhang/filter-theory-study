"""可编辑源文件的枚举与路径安全校验。"""
from __future__ import annotations

from pathlib import Path

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
        items.append(((grp, rel), {"path": rel, "size": st.st_size, "mtime_ns": str(st.st_mtime_ns)}))
    items.sort(key=lambda x: x[0])
    return [x[1] for x in items]
