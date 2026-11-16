"""跨文件全文搜索。"""
from __future__ import annotations

import re
from pathlib import Path

from .files import _list_editable_files

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
