"""受控 Markdown 的扩展块：管道表格编译与脚注收集渲染。"""
from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING

from .mdsyntax import MATH, PIPE_ROW, PIPE_SEP

if TYPE_CHECKING:
    from .mdinline import MarkdownInline

_CODE_RE = re.compile(r"`[^`\n]+`")
_XREF_RE = re.compile(r"\{@[^}\n]+\}")
_FN_PLACEHOLDER = re.compile(r"<!--\s*FOOTNOTES\s*-->")


def is_pipe_table_start(lines: list[str], idx: int) -> bool:
    """判断 lines[idx] 是否为标准 Markdown 管道表首行（下一行为分隔行）。"""
    return idx + 1 < len(lines) and bool(PIPE_ROW.match(lines[idx]) and PIPE_SEP.match(lines[idx + 1]))


def split_pipe_cells(line: str) -> list[str]:
    """在保护行内公式、行内代码、交叉引用与转义竖线后切分管道表单元格。"""
    stash: list[str] = []

    def _keep(m: re.Match[str]) -> str:
        stash.append(m.group(0))
        return f"\x00C{len(stash) - 1}\x00"

    protected = MATH.sub(_keep, line)
    protected = _CODE_RE.sub(_keep, protected)
    protected = _XREF_RE.sub(_keep, protected)
    protected = protected.replace(r"\|", "\x00PIPE\x00").strip()
    if protected.startswith("|"):
        protected = protected[1:]
    if protected.endswith("|"):
        protected = protected[:-1]
    cells: list[str] = []
    for raw in protected.split("|"):
        restored = re.sub(r"\x00C(\d+)\x00", lambda m: stash[int(m.group(1))], raw)
        cells.append(restored.replace("\x00PIPE\x00", "|").strip())
    return cells


def _parse_aligns(sep_line: str) -> list[str]:
    aligns: list[str] = []
    for col in split_pipe_cells(sep_line):
        c = col.strip()
        if c.startswith(":") and c.endswith(":"):
            aligns.append("center")
        elif c.endswith(":"):
            aligns.append("right")
        elif c.startswith(":"):
            aligns.append("left")
        else:
            aligns.append("")
    return aligns


def render_pipe_table(conv: MarkdownInline, pairs: list[tuple[int, str]], fname: str) -> str:
    """将 [(line_no, raw_line), ...] 管道表块编译为带源码锚点的 HTML <table>。"""
    ef = html.escape(fname, quote=True)
    l1, l2 = pairs[0][0], pairs[-1][0]
    head_ln, head_raw = pairs[0]
    aligns = _parse_aligns(pairs[1][1])

    def _cell_attr(idx: int) -> str:
        al = aligns[idx] if idx < len(aligns) else ""
        return f' style="text-align:{al}"' if al else ""

    ths = "".join(
        f"<th{_cell_attr(idx)}>{conv.inline(c)}</th>"
        for idx, c in enumerate(split_pipe_cells(head_raw))
    )
    thead = f'<thead><tr data-file="{ef}" data-l="{head_ln}">{ths}</tr></thead>'
    body_rows: list[str] = []
    for rln, rraw in pairs[2:]:
        tds = "".join(
            f"<td{_cell_attr(idx)}>{conv.inline(c)}</td>"
            for idx, c in enumerate(split_pipe_cells(rraw))
        )
        body_rows.append(f'<tr data-file="{ef}" data-l="{rln}">{tds}</tr>')
    tbody = f"<tbody>{''.join(body_rows)}</tbody>"
    return f'<table data-file="{ef}" data-l1="{l1}" data-l2="{l2}">{thead}{tbody}</table>'


def footnotes_html(footnotes: dict[str, str]) -> str:
    """将收集到的脚注字典渲染为文末 <section class="footnotes">。"""
    if not footnotes:
        return ""
    items = "".join(
        f'<li id="fn-{html.escape(fid, quote=True)}">{body} '
        f'<a class="fn-back" href="#fnref-{html.escape(fid, quote=True)}" aria-label="返回正文">↩</a></li>'
        for fid, body in footnotes.items()
    )
    return f'<section class="footnotes"><ol class="fn-list">{items}</ol></section>'


def apply_footnotes(conv: MarkdownInline, doc: str) -> str:
    """校验全部行内脚注引用是否已定义，并展开或追加脚注区块。"""
    seen_missing: set[str] = set()
    for fid in conv.fn_refs:
        if fid not in conv.footnotes and fid not in seen_missing:
            seen_missing.add(fid)
            conv.errors.append(f"未定义脚注：[^{fid}]")
    fn_sec = footnotes_html(conv.footnotes)
    if _FN_PLACEHOLDER.search(doc):
        return _FN_PLACEHOLDER.sub(lambda _: fn_sec, doc)
    if fn_sec:
        return f"{doc}\n{fn_sec}" if doc else fn_sec
    return doc
