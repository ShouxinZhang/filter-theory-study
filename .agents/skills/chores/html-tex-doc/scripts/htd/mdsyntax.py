"""受控 Markdown 的行级语法正则与小工具。"""
from __future__ import annotations

import re

MATH = re.compile(r"(?<![\\$])\$(?!\$)(.+?)(?<![\\$])\$", re.S)

FENCE_OPEN = re.compile(r"^\$\$\s*(?:\{#([^}]+)\})?\s*$")

FENCE_CLOSE = re.compile(r"^\$\$\s*(?:\{#([^}]+)\})?\s*$")

HEAD = re.compile(r"^(#{1,3})\s+(.*?)(?:\s*\{#([^}]+)\})?\s*$")

BOX_OPEN = re.compile(
    r"^:::[ \t]*(\S+)(?:[ \t]+\{#([^\s}]+)(?:[ \t]+num=(\"[^\"]+\"|'[^']+'|[^\s}]+))?[ \t]*\})?[ \t]*(.*)$"
)

MD_FIG = re.compile(r"^!\[(.*?)\]\(([^)]+)\)\s*(?:\{#([^}]+)\})?\s*$")

ITEM = re.compile(r"^(\d+\.|-)\s+")

RAW = re.compile(r"^<(figure|table|header|div|nav|section|ol|ul|img|p|h[1-6]|blockquote|details|!--)")

FOOTNOTE_DEF = re.compile(r"^\[\^([\w-]+)\]:[ \t]*(.+)$")

PIPE_ROW = re.compile(r"^\s*\|")

PIPE_SEP = re.compile(r"^\s*\|(?:\s*:?-{2,}:?\s*\|)+\s*$")


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inject_attr(tag_html: str, extra: str) -> str:
    """向首个非注释 HTML 开标签注入源位置属性。"""
    if tag_html.lstrip().startswith("<!--"):
        return tag_html
    return re.sub(
        r"^(\s*<[a-zA-Z][\w:-]*\b)([^>]*?)(/?)>",
        lambda m: m.group(0) if "data-file=" in m.group(2) else f"{m.group(1)}{m.group(2)} {extra}{m.group(3)}>",
        tag_html,
        count=1,
    )
