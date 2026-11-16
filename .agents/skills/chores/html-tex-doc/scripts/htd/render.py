"""把编号、图、目录、交叉引用落到正文 HTML。"""
from __future__ import annotations

import re
from pathlib import Path

from .numbering import REF, _keep_loc, attrs
from .svgtheme import inline_svg
from .texfig import compile_tex
from .toc import _build_toc_html

def parse_macros(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    text = re.sub(r"(?<!\\)%.*", "", path.read_text(encoding="utf-8"))
    macros: dict[str, object] = {}
    for m in re.finditer(r"\\newcommand\{\\(\w+)\}(?:\[(\d)\])?\{", text):
        depth, i = 1, m.end()
        while depth and i < len(text):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        body = text[m.end() : i - 1]
        macros[m.group(1)] = [body, int(m.group(2))] if m.group(2) else body
    return macros


def render(
    doc: str,
    labels: dict[str, dict[str, str]],
    src_dir: Path,
    build_dir: Path,
    force: bool,
    errors: list[str],
) -> tuple[str, int]:
    n_svg = 0
    titles_by_id = {v["id"]: v["text"] for v in labels.values()}

    def sec_fn(m: re.Match[str]) -> str:
        tag, a, title = m.group(1), attrs(m.group(2)), m.group(3)
        L = labels[a["data-label"]]
        loc = _keep_loc(a)
        return f'<{tag} id="{L["id"]}"{loc}><span class="secnum">{L["num"]}</span>{title}</{tag}>'

    doc = re.sub(r"<(h[23])\b([^>]*)>(.*?)</\1>", sec_fn, doc, flags=re.S)

    # 收集 h2 / h3 / h4[id] 生成完整三级目录树
    toc: list[tuple[int, str, str, str]] = []
    for hm in re.finditer(r'<(h[234])\b([^>]*)><span class="secnum">(.*?)</span>(.*?)</\1>', doc, flags=re.S):
        tag, ha, num, raw_title = hm.group(1), attrs(hm.group(2)), hm.group(3), hm.group(4)
        if "id" not in ha:
            continue
        clean_title = re.sub(r"</?span\b[^>]*>", "", raw_title)
        lv = {"h2": 1, "h3": 2, "h4": 3}[tag]
        toc.append((lv, ha["id"], num, clean_title))

    def eq_fn(m: re.Match[str]) -> str:
        extra_cls, a, body = m.group(1), attrs(m.group(2)), m.group(3)
        if "data-label" not in a:
            return m.group(0)
        L = labels[a["data-label"]]
        i = body.rfind(r"\]")
        if i == -1:
            errors.append(f"{a['data-label']} 公式块未找到 \\] 结尾")
            return m.group(0)
        body = body[:i] + f"\\tag{{{L['num']}}} " + body[i:]
        loc = _keep_loc(a)
        return f'<div class="eq{extra_cls}" id="{L["id"]}"{loc}>{body}</div>'

    doc = re.sub(r'<div class="eq([^"]*)"([^>]*)>(.*?)</div>', eq_fn, doc, flags=re.S)

    def thm_open_fn(m: re.Match[str]) -> str:
        a, gap, p_open = attrs(m.group(1)), m.group(2), m.group(3)
        if "data-label" not in a:
            return m.group(0)
        L = labels[a["data-label"]]
        title = f"（{a['data-title']}）" if a.get("data-title") else ""
        head = f'<span class="thmhead">{L["text"]}</span><span class="thmtitle">{title}</span>　'
        loc = _keep_loc(a)
        return f'<div class="thm" id="{L["id"]}"{loc}>{gap}{p_open}{head}'

    doc = re.sub(r'<div class="thm"([^>]*)>(\s*)(<p\b[^>]*>)', thm_open_fn, doc, flags=re.S)

    def fig_fn(m: re.Match[str]) -> str:
        nonlocal n_svg
        cls, a, body = m.group(1), attrs(m.group(2)), m.group(3)
        L = labels[a["data-label"]]
        body = re.sub(
            r"<figcaption(\b[^>]*)>",
            lambda fm: f'<figcaption{fm.group(1)}><span class="caplabel">{L["text"]}</span>',
            body,
            count=1,
        )
        if a.get("data-tex"):
            if "<!--TEX-->" not in body:
                errors.append(f"{a['data-label']} 缺少 <!--TEX--> 占位注释")
            svg = compile_tex(a["data-tex"], src_dir, build_dir, force, errors)
            if svg:
                n_svg += 1
                body = body.replace("<!--TEX-->", inline_svg(svg, L["id"], L["text"], titles_by_id))
        loc = _keep_loc(a, include_tex=True)
        return f'<figure class="{cls}" id="{L["id"]}"{loc}>{body}</figure>'

    doc = re.sub(r'<figure class="(fig|alg|tbl)"([^>]*)>(.*?)</figure>', fig_fn, doc, flags=re.S)

    if "<!--TOC-->" in doc and toc:
        doc = doc.replace("<!--TOC-->", _build_toc_html(toc))
    else:
        doc = doc.replace("<!--TOC-->", "")

    def ref_fn(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in labels:
            errors.append(f"HTML 侧未定义引用：{key}")
            return '<span class="xref-missing">??</span>'
        L = labels[key]
        return f'<a class="xref" href="#{L["id"]}">{L["num"] if m.group(2) else L["text"]}</a>'

    return REF.sub(ref_fn, doc), n_svg
