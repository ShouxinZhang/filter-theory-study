"""受控 Markdown 的行内层：公式、斜体、脚注、引用、文献、带源码锚点的行与列表项。"""
from __future__ import annotations

import html
import re
from .bib import fmt_ref
from .mdsyntax import FENCE_CLOSE, FENCE_OPEN, MATH, esc
from .numbering import REF


class MarkdownInline:
    def __init__(self, bib: dict[str, dict[str, str]] | None = None, bib_order: str | None = None):
        self.bib = bib or {}
        self.bib_order = bib_order
        self.cites: list[str] = list(self.bib.keys()) if bib_order == "file" else []
        self.footnotes: dict[str, str] = {}
        self.fn_refs: list[str] = []
        self._fn_seen: set[str] = set()
        self.errors: list[str] = []
        self.auto = 0
        self.sec = [0, 0, 0]
        self.sub: dict[str, tuple[str, str]] = {}

    def _cite(self, m: re.Match[str]) -> str:
        items: list[tuple[int, str]] = []
        for k in re.split(r"\s*[,;]\s*@?", m.group(1).strip()):
            if not k:
                continue
            if k not in self.bib:
                self.errors.append(f"未知文献键：{k}")
                continue
            if k not in self.cites:
                self.cites.append(k)
            items.append((self.cites.index(k) + 1, k))
        if not items:
            return m.group(0)

        def _link(idx: int, key: str) -> str:
            return f'<a class="cite" href="#ref-{key}">{idx}</a>'

        if self.bib_order != "file":
            return '<sup class="cites">[' + ",".join(_link(idx, k) for idx, k in items) + "]</sup>"
        runs: list[list[tuple[int, str]]] = [[items[0]]]
        for idx, k in items[1:]:
            if idx == runs[-1][-1][0] + 1:
                runs[-1].append((idx, k))
            else:
                runs.append([(idx, k)])
        parts: list[str] = []
        for r in runs:
            if len(r) >= 3:
                parts.append(f"{_link(*r[0])}–{_link(*r[-1])}")
            else:
                parts.extend(_link(idx, k) for idx, k in r)
        return '<sup class="cites">[' + ",".join(parts) + "]</sup>"

    def _fn_ref(self, m: re.Match[str]) -> str:
        fid = m.group(1)
        self.fn_refs.append(fid)
        efid = html.escape(fid, quote=True)
        id_attr = "" if fid in self._fn_seen else f' id="fnref-{efid}"'
        self._fn_seen.add(fid)
        return f'<sup class="fnref"><a class="xref" href="#fn-{efid}"{id_attr}>[{efid}]</a></sup>'

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
        s = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<em>\1</em>", s)
        s = re.sub(r"\[@([^\]]+)\]", self._cite, s)
        s = re.sub(r"\[\^([\w-]+)\](?!:)", self._fn_ref, s)
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

    def eq(self, label: str | None, body: str, fname: str, l1: int, l2: int, extra_cls: str = "") -> str:
        ef = html.escape(fname, quote=True)
        lab = f' data-label="{html.escape(label, quote=True)}"' if label else ""
        cls = f"eq {extra_cls}".strip()
        return f'<div class="{cls}"{lab} data-file="{ef}" data-l1="{l1}" data-l2="{l2}">\n\\[ {esc(body)} \\]\n</div>'

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
            key, mod = m.group(1), m.group(2)
            if key not in self.sub:
                return m.group(0)
            num, anc = self.sub[key]
            disp = f"第 {num} 节" if mod is None else (num if mod == "n" else mod)
            return f'<a class="xref" href="#{anc}">{disp}</a>'

        return REF.sub(fn, doc)

    def refs_html(self) -> str:
        if not self.cites:
            return ""
        return '<ol class="refs">' + "".join(
            f'<li id="ref-{html.escape(k, quote=True)}">{fmt_ref(self.bib[k])}</li>' for k in self.cites
        ) + "</ol>"
