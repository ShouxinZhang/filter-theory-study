"""浮动体编解码（table / figure / algorithm）与 standalone 算法提取。"""
from __future__ import annotations

from pathlib import Path
import re
from .inline import KALMAN_SPEC, SyncSpec, grab_braced, grab_bracketed, md_inline_to_tex, strip_tex_comment, tex_inline_to_md


def cmd_arg(text: str, cmd: str) -> str:
    pos = 0
    while (idx := text.find(cmd, pos)) != -1:
        end = idx + len(cmd)
        if end < len(text) and text[end].isalpha():
            pos = end; continue
        k = end + len(text[end:]) - len(text[end:].lstrip(" \t"))
        if k < len(text) and text[k] == "[" and (br := grab_bracketed(text, k)):
            k = br[1] + len(text[br[1]:]) - len(text[br[1]:].lstrip(" \t"))
        if k < len(text) and text[k] == "{" and (res := grab_braced(text, k)):
            return res[0]
        pos = end
    return ""


def _tag_inner(tag: str, s: str) -> str:
    return m.group(1) if (m := re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", s, re.S)) else ""


def _no_comments(tex_block: str) -> str:
    return "\n".join(strip_tex_comment(ln) for ln in tex_block.split("\n") if not re.match(r"^\s*%", ln))


def _scan_tex_table(s: str, *, by_row: bool) -> list[str]:
    items, start, i, depth, in_math = [], 0, 0, 0, False
    while i < len(s):
        if not by_row and s.startswith(r"\texttt{", i) and not in_math and (cr := grab_braced(s, i + 7)):
            i = cr[1]
        elif by_row and s.startswith("\\\\", i) and not in_math and depth == 0:
            if seg := s[start:i].strip():
                items.append(seg)
            i += 2
            i = br[1] if (i < len(s) and s[i] == "[" and (br := grab_bracketed(s, i))) else i
            start = i
        elif not by_row and not in_math and depth == 0 and s[i] == "&":
            items.append(s[start:i].strip()); start = i = i + 1
        elif s[i] == "\\" and i + 1 < len(s):
            i += 2
        else:
            in_math = (not in_math) if s[i] == "$" else in_math
            depth = max(0, depth + (1 if s[i] == "{" else -1)) if (not in_math and s[i] in "{}") else depth
            i += 1
    tail = s[start:].strip()
    return ([*items, tail] if tail else items) if by_row else [*items, tail]


def tex_table_parts(tex_block: str) -> tuple[list[list[str]], list[list[str]], str]:
    no_cmt = _no_comments(tex_block)
    m = re.search(r"\\toprule(?:\[[^\]]*\])?(.*?)\\midrule(?:\[[^\]]*\])?(.*?)\\bottomrule(?:\[[^\]]*\])?", no_cmt, re.S)
    rows = lambda seg: [_scan_tex_table(r, by_row=False) for r in _scan_tex_table(seg, by_row=True)]
    return (rows(m.group(1)), rows(m.group(2)), no_cmt) if m else ([], [], no_cmt)


def tex_htdtable_to_md(raw_blk: str, spec: SyncSpec) -> str:
    hr, br, _ = tex_table_parts(raw_blk)
    h_md = [tex_inline_to_md(c, spec) for c in (hr[0] if hr else [])]
    return "\n".join(["| " + " | ".join(h_md) + " |", "| " + " | ".join("---" for _ in h_md) + " |", *("| " + " | ".join(tex_inline_to_md(c, spec) for c in r) + " |" for r in br)])


def tex_table_to_md(raw_blk: str, spec: SyncSpec) -> tuple[str, str]:
    hr, br, no_cmt = tex_table_parts(raw_blk)
    cap_md, lab = tex_inline_to_md(cmd_arg(no_cmt, r"\caption"), spec), cmd_arg(no_cmt, r"\label")
    thead = "".join("<tr>" + "".join(f"<th>{tex_inline_to_md(c, spec)}</th>" for c in r) + "</tr>" for r in hr)
    tbody = "\n".join("<tr>" + "".join(f"<td>{tex_inline_to_md(c, spec)}</td>" for c in r) + "</tr>" for r in br)
    return f'<figure class="tbl" data-label="{lab}">\n<figcaption>{cap_md}</figcaption>\n<table>\n<thead>{thead}</thead>\n<tbody>\n{tbody}\n</tbody>\n</table>\n</figure>', lab


def tex_figure_to_md(raw_blk: str, spec: SyncSpec) -> tuple[str, str]:
    no_cmt = _no_comments(raw_blk)
    imgs = [f'<img src="figs/{Path(res[0].strip()).stem}.svg" alt="">' for m in re.finditer(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{", no_cmt) if (res := grab_braced(no_cmt, m.end() - 1))]
    cap_md, lab = tex_inline_to_md(cmd_arg(no_cmt, r"\caption"), spec).replace("\n\n", "\n"), cmd_arg(no_cmt, r"\label")
    d_lab = f' data-label="{lab}"' if lab else ""
    return "\n".join([f'<figure class="fig"{d_lab}>', *imgs, f"<figcaption>{cap_md}</figcaption>", "</figure>"]), lab


def alg_name_from_label(lab: str, idx: int = 1) -> str:
    return re.sub(r"[^\w.-]", "-", (lab.split(":")[-1].strip() if lab else "")).strip("-") or f"alg-{idx}"


def tex_algorithm_to_md(raw_blk: str, spec: SyncSpec, idx: int = 1) -> tuple[str, str]:
    no_cmt = _no_comments(raw_blk)
    cap_md, lab = tex_inline_to_md(cmd_arg(no_cmt, r"\caption"), spec).replace("\n\n", "\n"), cmd_arg(no_cmt, r"\label")
    name, d_lab = alg_name_from_label(lab, idx), (f' data-label="{lab}"' if lab else "")
    return f'<figure class="alg"{d_lab} data-tex="algs/{name}.tex">\n<figcaption>{cap_md}</figcaption>\n<!--TEX-->\n</figure>', lab


def _strip_cmd_calls(line: str, cmds: tuple[str, ...]) -> str:
    out, i, n = [], 0, len(line)
    while i < n:
        if hit := next((c for c in cmds if line.startswith(c, i) and (i + len(c) == n or not line[i + len(c)].isalpha())), None):
            k = i + len(hit) + len(line[i + len(hit):]) - len(line[i + len(hit):].lstrip(" \t"))
            if k < n and line[k] == "[" and (br := grab_bracketed(line, k)):
                k = br[1] + len(line[br[1]:]) - len(line[br[1]:].lstrip(" \t"))
            if k < n and line[k] == "{" and (cr := grab_braced(line, k)):
                i = cr[1]; continue
        out.append(line[i]); i += 1
    return "".join(out)


def _alg_refs_to_cref(text: str, spec: SyncSpec) -> str:
    for pf, op, sf in spec.ref_templates:
        text = re.sub(re.escape(op) + r"([\w:.-]+)\}" + re.escape(sf), lambda m, p=pf: rf"\cref{{{m.group(1)}}}" if (m.group(1).startswith(p) or f":{p}" in m.group(1)) else m.group(0), text)
    return re.sub(r"\\(?:eq)?ref\{([\w:.-]+)\}", r"\\cref{\1}", text)


def extract_alg_standalone(raw_alg_block: str, spec: SyncSpec = KALMAN_SPEC, idx: int = 1) -> tuple[str, str]:
    lab = cmd_arg(_no_comments(raw_alg_block), r"\label")
    rel = f"algs/{alg_name_from_label(lab, idx)}.tex"
    body_lines: list[str] = []
    for ln in raw_alg_block.split("\n"):
        if re.match(r"^\s*%", ln):
            continue
        cleaned = re.sub(r"^(\s*\\begin\{algorithm\})(?:\[[^\]]*\])?", r"\1[H]", strip_tex_comment(ln))
        stripped = _strip_cmd_calls(cleaned, (r"\caption", r"\label"))
        if stripped == cleaned or stripped.strip():
            body_lines.append(_alg_refs_to_cref(stripped, spec))
    body = "\n".join(body_lines).strip()
    inc = r"\input{algcommon}" if r"\begin{algorithmic}" in body else r"\input{alg2e}"
    doc = "\n".join([r"\documentclass[varwidth=15cm,border=1pt]{standalone}", r"\input{common}", r"\usepackage{bm,mathrsfs}", inc, r"\begin{document}", body, r"\end{document}", ""])
    return rel, doc


def md_figure_block_to_unit_fields(blk: str, spec: SyncSpec) -> tuple[str, str, str]:
    cls = m.group(1) if (m := re.match(r'^<figure\s+class="(tbl|fig|alg)"', blk)) else "tbl"
    lab = m.group(1) if (m := re.search(r'data-label="([^"]*)"', blk)) else ""
    if cls in ("fig", "alg"):
        return ("figure" if cls == "fig" else "algorithm"), "", lab
    cap = md_inline_to_tex(_tag_inner("figcaption", blk), spec)
    ths = [md_inline_to_tex(c, spec) for c in re.findall(r"<th[^>]*>(.*?)</th>", _tag_inner("thead", blk), re.S)]
    trs = [" & ".join(md_inline_to_tex(c, spec) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)) + r" \\" for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", _tag_inner("tbody", blk), re.S)]
    cspec = "cXX" if len(ths) == 3 else ("l" * max(0, len(ths) - 1) + "X")
    return "html_table", "\n".join([r"\begin{table}[htbp]", r"\centering", rf"\caption{{{cap}}}\label{{{lab}}}", rf"\begin{{tabularx}}{{\textwidth}}{{{cspec}}}", r"\toprule", " & ".join(ths) + r" \\", r"\midrule", *trs, r"\bottomrule", r"\end{tabularx}", r"\end{table}"]), lab
