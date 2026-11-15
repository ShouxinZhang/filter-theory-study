#!/usr/bin/env python3
"""受控学术 Markdown + BibTeX 前端转换器（为 html-tex-doc 生成带双层源行号锚点的 doc.html）。

支持特性：
- 多文件按序拼接（*.md），自动提取 <!-- title: ... -->、<!--TOC-->、<!--REFS-->；
- 章节标题 # / ## / ###（映射为 h2 / h3 / h4，支持三级编号与 {#label} 引用）；
- 行内公式 $...$，行间公式 $$ {#eq:key} ... $$（兼容闭合行 $$ {#eq:key}）；
- 定理与证明围栏块 ::: 定理 {#label} 标题 ... ::: 与 ::: 证明 ... :::；
- 简写图与算法 ![题注](figs/a.svg){#fig:a} / ![题注](algs/b.tex){#alg:b} 及原样 HTML 块；
- BibTeX 文献库 refs.bib 解析与 [@k1,k2] 按首次出现顺序编号；
- 双层 SyncMap 锚点：块级 data-file / data-l1 / data-l2 + 段内逐源行 <span class="sl" data-file data-l>。
"""
from __future__ import annotations

import html
import re
import unicodedata
from pathlib import Path

MATH = re.compile(r"(?<![\\$])\$(?!\$)(.+?)(?<![\\$])\$", re.S)
FENCE_OPEN = re.compile(r"^\$\$\s*(?:\{#([^}]+)\})?\s*$")
FENCE_CLOSE = re.compile(r"^\$\$\s*(?:\{#([^}]+)\})?\s*$")
HEAD = re.compile(r"^(#{1,3})\s+(.*?)(?:\s*\{#([^}]+)\})?\s*$")
BOX_OPEN = re.compile(r"^:::[ \t]*(\S+)(?:[ \t]+\{#([^}]+)\})?[ \t]*(.*)$")
MD_FIG = re.compile(r"^!\[(.*?)\]\(([^)]+)\)\s*(?:\{#([^}]+)\})?\s*$")
ITEM = re.compile(r"^(\d+\.|-)\s+")
RAW = re.compile(r"^<(figure|table|header|div|nav|section|ol|ul|img|p|h[1-6]|blockquote|details|!--)")


def _clean_bib_val(v: str) -> str:
    v = re.sub(
        r"""\\(["'`^~])\{?(\w)\}?""",
        lambda m: unicodedata.normalize(
            "NFC",
            m.group(2) + {'"': "\u0308", "'": "\u0301", "`": "\u0300", "^": "\u0302", "~": "\u0303"}[m.group(1)],
        ),
        v,
    )
    v = v.replace(r"\&", "&").replace("--", "–").replace("{", "").replace("}", "").replace("~", " ")
    return html.escape(" ".join(v.split()), quote=False)


def parse_bib(text: str) -> dict[str, dict[str, str]]:
    text = re.sub(r"^\s*%.*$", "", text, flags=re.M)
    out: dict[str, dict[str, str]] = {}
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        i, depth = m.end(), 1
        j = i
        while depth and j < len(text):
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        body, fields, pos = text[i : j - 1], {}, 0
        while fm := re.compile(r"\s*,?\s*(\w+)\s*=\s*").match(body, pos):
            k = fm.end()
            if body[k : k + 1] == "{":
                d, e = 1, k + 1
                while d and e < len(body):
                    d += {"{": 1, "}": -1}.get(body[e], 0)
                    e += 1
                val = body[k + 1 : e - 1]
            elif body[k : k + 1] == '"':
                e = body.index('"', k + 1) + 1
                val = body[k + 1 : e - 1]
            else:
                e = body.find(",", k)
                e = len(body) if e < 0 else e
                val = body[k:e]
            fields[fm.group(1).lower()] = val
            pos = e
        out[m.group(2)] = fields
    return out


def fmt_ref(f: dict[str, str]) -> str:
    names = []
    for a in re.split(r"\s+and\s+", f.get("author", "")):
        if "," in a and not a.strip().startswith("{"):
            last, first = a.split(",", 1)
            a = f"{first.strip()} {last.strip()}"
        if a.strip():
            names.append(_clean_bib_val(a))
    who = ", ".join(names[:3]) + (" et al." if len(names) > 3 else "")
    venue = next((f[k] for k in ("journal", "booktitle", "publisher", "school", "howpublished") if f.get(k)), "")
    bits = [
        who,
        _clean_bib_val(f.get("title", "")),
        f"<em>{_clean_bib_val(venue)}</em>" if venue else "",
        _clean_bib_val(f.get("year", "")),
    ]
    return ". ".join(b for b in bits if b) + "."


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


class MarkdownCompiler:
    def __init__(self, bib: dict[str, dict[str, str]] | None = None):
        self.bib = bib or {}
        self.cites: list[str] = []
        self.errors: list[str] = []
        self.auto = 0
        self.sec = [0, 0, 0]
        self.sub: dict[str, tuple[str, str]] = {}

    def _cite(self, m: re.Match[str]) -> str:
        out = []
        for k in re.split(r"\s*[,;]\s*@?", m.group(1).strip()):
            if not k:
                continue
            if k not in self.bib:
                self.errors.append(f"未知文献键：{k}")
                continue
            if k not in self.cites:
                self.cites.append(k)
            out.append(f'<a class="cite" href="#ref-{k}">{self.cites.index(k) + 1}</a>')
        return '<sup class="cites">[' + ",".join(out) + "]</sup>" if out else m.group(0)

    def inline(self, s: str) -> str:
        """单块行内转换（保持换行符个数不变，供逐源行切分使用）。"""
        stash: list[str] = []

        def keep_math(m: re.Match[str]) -> str:
            nl = "\n" * m.group(0).count("\n")
            stash.append(r"\(" + esc(m.group(1)) + r"\)")
            return f"\x00M{len(stash) - 1}\x00{nl}"

        def keep_code(m: re.Match[str]) -> str:
            stash.append(f"<code>{esc(m.group(1))}</code>")
            return f"\x00M{len(stash) - 1}\x00"

        s = MATH.sub(keep_math, s).replace(r"\$", "$")
        s = re.sub(r"`([^`\n]+)`", keep_code, s)
        s = re.sub(
            r"\*\*(.+?)\*\*",
            lambda m: "\n".join(f"<strong>{p}</strong>" if p else "" for p in m.group(1).split("\n")),
            s,
            flags=re.S,
        )
        s = re.sub(r"\[@([^\]]+)\]", self._cite, s)
        return re.sub(r"\x00M(\d+)\x00", lambda m: stash[int(m.group(1))], s)

    def render_lines_with_spans(self, pairs: list[tuple[int, str]], fname: str, prefix: str = "") -> str:
        """将 [(line_no, raw_line), ...] 渲染为逐源行 <span class="sl" data-file data-l>。"""
        if not pairs:
            return ""
        ef = html.escape(fname, quote=True)
        joined = "\n".join(t for _, t in pairs)
        rendered = self.inline(joined).split("\n")
        spans: list[str] = []
        used_prefix = False
        for (ln, _), seg in zip(pairs, rendered):
            if not seg.strip() and not (prefix and not used_prefix):
                continue
            pre = ""
            if prefix and not used_prefix:
                pre, used_prefix = prefix, True
            spans.append(f'<span class="sl" data-file="{ef}" data-l="{ln}">{pre}{seg}</span>')
        if prefix and not used_prefix:
            ln0 = pairs[0][0]
            spans.append(f'<span class="sl" data-file="{ef}" data-l="{ln0}">{prefix}</span>')
        return "\n".join(spans)

    def eq(self, label: str | None, body: str, fname: str, l1: int, l2: int) -> str:
        ef = html.escape(fname, quote=True)
        lab = f' data-label="{html.escape(label, quote=True)}"' if label else ""
        return f'<div class="eq"{lab} data-file="{ef}" data-l1="{l1}" data-l2="{l2}">\n\\[ {esc(body)} \\]\n</div>'

    def _render_item(self, pairs: list[tuple[int, str]], fname: str) -> str:
        """列表项内部：支持文字行与内嵌 $$ 公式块。"""
        out: list[str] = []
        buf: list[tuple[int, str]] = []
        i = 0
        while i < len(pairs):
            ln, txt = pairs[i]
            if m := FENCE_OPEN.match(txt):
                if buf:
                    out.append(self.render_lines_with_spans(buf, fname))
                    buf = []
                j = i + 1
                close_lab = None
                while j < len(pairs):
                    cm = FENCE_CLOSE.match(pairs[j][1].strip())
                    if cm:
                        close_lab = cm.group(1)
                        break
                    j += 1
                end_idx = min(j, len(pairs) - 1)
                lab = m.group(1) or close_lab
                body = "\n".join(p[1] for p in pairs[i + 1 : j])
                out.append(self.eq(lab, body, fname, ln, pairs[end_idx][0]))
                i = j + 1
            else:
                buf.append((ln, txt))
                i += 1
        if buf:
            out.append(self.render_lines_with_spans(buf, fname))
        return "\n".join(x for x in out if x)

    def _md_figure(self, m: re.Match[str], fname: str, ln: int) -> str:
        cap, path, lab = self.inline(m.group(1)), m.group(2).strip(), m.group(3) or ""
        ef = html.escape(fname, quote=True)
        if not lab:
            self.auto += 1
            lab = f"fig:auto-{self.auto}"
        el = html.escape(lab, quote=True)
        ep = html.escape(path, quote=True)
        loc = f'data-file="{ef}" data-l="{ln}" data-l1="{ln}" data-l2="{ln}"'
        if path.endswith(".tex"):
            cls = "alg" if lab.startswith("alg:") or "/algs/" in f"/{path}" or path.startswith("algs/") else "fig"
            return f'<figure class="{cls}" data-label="{el}" data-tex="{ep}" {loc}>\n<figcaption>{cap}</figcaption>\n<!--TEX-->\n</figure>'
        return f'<figure class="fig" data-label="{el}" {loc}>\n<img src="{ep}" alt="">\n<figcaption>{cap}</figcaption>\n</figure>'

    def link_subsections(self, doc: str) -> str:
        def fn(m: re.Match[str]) -> str:
            if m.group(1) not in self.sub:
                return m.group(0)
            num, anchor = self.sub[m.group(1)]
            return f'<a class="xref" href="#{anchor}">{num if m.group(2) else f"第 {num} 节"}</a>'

        return re.sub(r"\{@([\w:.-]+)(\|n)?\}", fn, doc)

    def refs_html(self) -> str:
        if not self.cites:
            return ""
        return '<ol class="refs">' + "".join(
            f'<li id="ref-{html.escape(k, quote=True)}">{fmt_ref(self.bib[k])}</li>' for k in self.cites
        ) + "</ol>"

    def convert(self, text: str, fname: str) -> str:
        ef = html.escape(fname, quote=True)
        out: list[str] = []
        para: list[tuple[int, str]] = []
        # stack entries: (kind_type, open_line, out_index, base_tag_prefix)
        stack: list[tuple[str, int, int, str]] = []
        prefix = ""
        lines = text.split("\n")
        i = 0

        def flush() -> None:
            nonlocal prefix
            if para:
                l1, l2 = para[0][0], para[-1][0]
                inner = self.render_lines_with_spans(para, fname, prefix)
                out.append(f'<p data-file="{ef}" data-l1="{l1}" data-l2="{l2}">{inner}</p>')
                prefix = ""
                para.clear()

        while i < len(lines):
            ln = i + 1
            line = lines[i].rstrip()
            if m := FENCE_OPEN.match(line):
                flush()
                j = i + 1
                close_lab = None
                while j < len(lines):
                    cm = FENCE_CLOSE.match(lines[j].strip())
                    if cm:
                        close_lab = cm.group(1)
                        break
                    j += 1
                if j == len(lines):
                    self.errors.append(f"{fname}:{ln} 行间公式 $$ 未闭合")
                    end_ln = len(lines)
                else:
                    end_ln = j + 1
                lab = m.group(1) or close_lab
                out.append(self.eq(lab, "\n".join(lines[i + 1 : j]), fname, ln, end_ln))
                i = j + 1
                continue

            if not line.strip():
                flush()
            elif line.strip() == ":::":
                flush()
                if not stack:
                    self.errors.append(f"{fname}:{ln} 多余的 :::")
                else:
                    ktype, open_ln, idx, tag_head = stack.pop()
                    out[idx] = f'{tag_head} data-file="{ef}" data-l1="{open_ln}" data-l2="{ln}">'
                    if ktype == "proof":
                        out.append('<p class="qed">∎</p>')
                out.append("</div>")
            elif m := BOX_OPEN.match(line):
                flush()
                kind, label, title = m.group(1), m.group(2), m.group(3).strip()
                idx = len(out)
                if kind in ("证明", "proof"):
                    stack.append(("proof", ln, idx, '<div class="proof"'))
                    out.append('<div class="proof">')
                    prefix = f"<em>{self.inline(title) if title else '证明'}.</em> "
                else:
                    thm_map = {
                        "theorem": "定理",
                        "lemma": "引理",
                        "proposition": "命题",
                        "definition": "定义",
                        "corollary": "推论",
                        "assumption": "假设",
                        "remark": "注",
                    }
                    disp_kind = thm_map.get(kind.lower(), kind)
                    if not label:
                        self.auto += 1
                        label = f"thm:auto-{self.auto}"
                    t = f' data-title="{html.escape(title, quote=True)}"' if title else ""
                    head_prefix = f'<div class="thm" data-kind="{html.escape(disp_kind, quote=True)}" data-label="{html.escape(label, quote=True)}"{t}'
                    stack.append(("thm", ln, idx, head_prefix))
                    out.append(head_prefix + ">")
            elif (m := HEAD.match(line)) and not para:
                lv = len(m.group(1))
                self.sec = self.sec[: lv - 1] + [self.sec[lv - 1] + 1] + [0] * (3 - lv)
                loc = f'data-file="{ef}" data-l="{ln}" data-l1="{ln}" data-l2="{ln}"'
                if lv == 3:
                    num = ".".join(map(str, self.sec))
                    anchor = re.sub(r"[^\w-]", "-", m.group(3) or f"sub-{num}")
                    if m.group(3):
                        self.sub[m.group(3)] = (num, anchor)
                    out.append(f'<h4 id="{anchor}" {loc}><span class="secnum">{num}</span>{self.inline(m.group(2))}</h4>')
                else:
                    lab = f' data-label="{html.escape(m.group(3), quote=True)}"' if m.group(3) else ""
                    out.append(f"<h{lv + 1}{lab} {loc}>{self.inline(m.group(2))}</h{lv + 1}>")
            elif (m := MD_FIG.match(line)) and not para:
                out.append(self._md_figure(m, fname, ln))
            elif not para and (RAW.match(line) or ITEM.match(line)):
                # 若以 <!-- 开头且多行注释，扫描至 -->；普通块扫描至空行
                if line.lstrip().startswith("<!--") and "-->" not in line:
                    j = i + 1
                    while j < len(lines) and "-->" not in lines[j]:
                        j += 1
                    j = min(j + 1, len(lines))
                    out.append("\n".join(lines[i:j]))
                    i = j
                    continue

                j = i
                while j < len(lines) and lines[j].strip():
                    j += 1
                block_pairs = [(k + 1, lines[k].rstrip()) for k in range(i, j)]
                l1, l2 = block_pairs[0][0], block_pairs[-1][0]

                if RAW.match(line):
                    rendered_raw: list[str] = []
                    for idx_b, (bln, bline) in enumerate(block_pairs):
                        rline = self.inline(bline)
                        if idx_b == 0:
                            rline = _inject_attr(rline, f'data-file="{ef}" data-l1="{l1}" data-l2="{l2}"')
                        elif re.match(r"^\s*<(tr|figcaption|p|li|h[1-6])\b", rline):
                            rline = _inject_attr(rline, f'data-file="{ef}" data-l="{bln}"')
                        rendered_raw.append(rline)
                    out.append("\n".join(rendered_raw))
                else:
                    items: list[list[tuple[int, str]]] = []
                    for bln, bline in block_pairs:
                        if ITEM.match(bline):
                            items.append([(bln, ITEM.sub("", bline, 1))])
                        else:
                            items[-1].append((bln, bline.strip()))
                    tag = "ul" if line.startswith("-") else "ol"
                    li_html = "".join(
                        f'<li data-file="{ef}" data-l1="{it[0][0]}" data-l2="{it[-1][0]}">{self._render_item(it, fname)}</li>'
                        for it in items
                    )
                    out.append(f'<{tag} data-file="{ef}" data-l1="{l1}" data-l2="{l2}">{li_html}</{tag}>')
                i = j
                continue
            else:
                para.append((ln, line))
            i += 1

        flush()
        if stack:
            self.errors.append(f"{fname} 末尾有未闭合的 ::: 块")
            for _, open_ln, idx, tag_head in reversed(stack):
                out[idx] = f'{tag_head} data-file="{ef}" data-l1="{open_ln}" data-l2="{len(lines)}">'
                out.append("</div>")
        return "\n".join(out)


def compile_markdown_dir(src_dir: Path) -> tuple[str, list[str]]:
    """将 src_dir 下的 *.md (+ 可选 refs.bib) 编译为完整 doc.html 字符串与错误列表。"""
    md_files = sorted(src_dir.glob("*.md"))
    bib_path = src_dir / "refs.bib"
    bib = parse_bib(bib_path.read_text(encoding="utf-8")) if bib_path.exists() else {}
    conv = MarkdownCompiler(bib)
    parts = [conv.convert(f.read_text(encoding="utf-8"), f.name) for f in md_files]
    doc = conv.link_subsections("\n".join(parts)).replace("<!--REFS-->", conv.refs_html())
    return doc, conv.errors
