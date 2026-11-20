"""论文工作区元信息提取、main.md 前置块解析与论文库自动发现。"""
from __future__ import annotations

from dataclasses import dataclass
import html
from pathlib import Path
import re

INCLUDE_RE = re.compile(r"^\s*<!--\s*include\s+([^\s]+?)\s*-->\s*$")
_TITLE_COMMENT_RE = re.compile(r"<!--\s*title:\s*(.*?)\s*-->")
_H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
_SKIP_DIRS = {"build", "outputs", "src", "node_modules", "__pycache__", "public-references"}


@dataclass
class PaperMeta:
    title: str | None = None
    macros: str | None = None
    bib: str | None = None
    bib_order: str | None = None
    lang: str | None = None
    entry: str | None = None


def parse_frontmatter(text: str) -> tuple[dict[str, str], str, int]:
    """解析 YAML-lite 前置块，返回 (键值表, 剩余正文, 剩余正文在原文件中的 1-based 起始行号)。"""
    lines = text.split("\n")
    if not lines or lines[0].lstrip("\ufeff").rstrip() != "---":
        return {}, text, 1
    end_idx: int | None = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return {}, text, 1

    meta: dict[str, str] = {}
    for raw in lines[1:end_idx]:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if ":" not in s:
            return {}, text, 1
        key, _, val = s.partition(":")
        k = key.strip()
        if not k or any(ch.isspace() for ch in k):
            return {}, text, 1
        v = val.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
            v = v[1:-1]
        meta[k] = v

    rest = "\n".join(lines[end_idx + 1 :])
    return meta, rest, end_idx + 2


def resolve_in_src(src_dir: Path, raw_rel: str) -> tuple[Path, str] | None:
    """将相对路径解析并限制在 src_dir 内，越界或含非法字符时返回 None。"""
    if not raw_rel or "\x00" in raw_rel or "\\" in raw_rel or Path(raw_rel).is_absolute():
        return None
    root = src_dir.resolve()
    try:
        target = (root / raw_rel).resolve()
        rel_posix = target.relative_to(root).as_posix()
    except (ValueError, OSError):
        return None
    return target, rel_posix


def _extract_comment_title(text: str) -> str | None:
    m = _TITLE_COMMENT_RE.search(text)
    if not m:
        return None
    t = m.group(1).strip()
    return t or None


def _extract_html_title(text: str) -> str | None:
    t = _extract_comment_title(text)
    if t:
        return t
    m = _H1_RE.search(text)
    if not m:
        return None
    plain = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))
    cleaned = " ".join(plain.split()).strip()
    return cleaned or None


def read_paper_meta(src_dir: Path) -> PaperMeta:
    """从工程 src/ 目录提取标题、导言预设与入口类型。"""
    if not src_dir.is_dir():
        return PaperMeta()
    root = src_dir.resolve()
    main_path = root / "main.md"
    if main_path.is_file():
        try:
            main_text = main_path.read_text(encoding="utf-8")
        except OSError:
            return PaperMeta(entry="main.md")
        fm, body, _ = parse_frontmatter(main_text)
        title = fm.get("title") or None
        macros = fm.get("macros") or None
        bib = fm.get("bib") or None
        bib_order = fm.get("bib_order") or None
        lang = fm.get("lang") or None
        if not title:
            title = _extract_comment_title(body)
        if not title:
            for line in body.split("\n"):
                im = INCLUDE_RE.match(line)
                if not im:
                    continue
                resolved = resolve_in_src(root, im.group(1))
                if resolved is None:
                    continue
                inc_path, _ = resolved
                if inc_path == main_path or not inc_path.is_file():
                    continue
                try:
                    title = _extract_comment_title(inc_path.read_text(encoding="utf-8"))
                except OSError:
                    title = None
                break
        return PaperMeta(title=title, macros=macros, bib=bib, bib_order=bib_order, lang=lang, entry="main.md")

    md_files = sorted(p for p in root.glob("*.md") if p.is_file())
    if md_files:
        try:
            first_text = md_files[0].read_text(encoding="utf-8")
        except OSError:
            first_text = ""
        return PaperMeta(title=_extract_comment_title(first_text), entry="*.md")

    doc_path = root / "doc.html"
    if doc_path.is_file():
        try:
            doc_text = doc_path.read_text(encoding="utf-8")
        except OSError:
            doc_text = ""
        return PaperMeta(title=_extract_html_title(doc_text), entry="doc.html")

    return PaperMeta()


def discover_papers(library_root: Path, max_depth: int = 2) -> list[dict[str, str]]:
    """在 library_root 下向下扫描 1..max_depth 层子目录，自动发现有效论文工程。"""
    if max_depth < 1 or not library_root.is_dir():
        return []
    root = library_root.resolve()
    found: list[dict[str, str]] = []

    def _walk(cur: Path, depth: int) -> None:
        try:
            children = sorted(cur.iterdir(), key=lambda p: p.name)
        except OSError:
            return
        for d in children:
            if d.name.startswith(".") or d.name in _SKIP_DIRS or not d.is_dir():
                continue
            src = d / "src"
            if src.is_dir():
                meta = read_paper_meta(src)
                if meta.entry is not None:
                    rel_posix = d.relative_to(root).as_posix()
                    found.append({"id": rel_posix, "title": meta.title or d.name, "entry": meta.entry})
                    continue
            if depth < max_depth:
                _walk(d, depth + 1)

    _walk(root, 1)
    found.sort(key=lambda item: item["id"])
    return found
