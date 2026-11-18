"""块级双向语法编解码（parse_tex_units / parse_md_units / tex_to_md / md_to_tex）。"""
from __future__ import annotations

from dataclasses import dataclass
import re
from ..mdblocks import split_pipe_cells
from ..mdsyntax import BOX_OPEN, FENCE_OPEN, FOOTNOTE_DEF, HEAD, PIPE_SEP
from .inline import KALMAN_SPEC, SyncSpec, grab_braced, grab_bracketed, md_inline_to_tex, strip_tex_comment, tex_inline_to_md

_MD_FIG_RE = re.compile(r"^!\[(.*)\]\(([^()\s]+)\)\s*(?:\{#([^}]+)\})?\s*$")
_P_H2_RE = re.compile(r'^<p class="h2">(.*)</p>\s*$')
_SEC_LV = {1: "section", 2: "subsection", 3: "subsubsection"}
_LV_BY_SEC = {v: k for k, v in _SEC_LV.items()}


@dataclass
class Unit:
    kind: str; md_text: str; tex_text: str; trailing_sep: str = ""; leading_comments: str = ""; line: int = 1; meta: str = ""


TexUnit = MdUnit = Unit


def _cmd_arg(text: str, cmd: str) -> str:
    return res[0] if ((idx := text.find(cmd + "{")) != -1 and (res := grab_braced(text, idx + len(cmd)))) else ""

def _grab_seq(text: str, count: int) -> list[str]:
    pos, out = text.find("{"), []
    for _ in range(count):
        if pos == -1 or not (res := grab_braced(text, pos)):
            return [""] * count
        out.append(res[0]); pos = text.find("{", res[1])
    return out


def _tag_inner(tag: str, s: str) -> str:
    return m.group(1) if (m := re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", s, re.S)) else ""


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


def _tex_table_parts(tex_block: str) -> tuple[list[list[str]], list[list[str]], str]:
    no_cmt = "\n".join(strip_tex_comment(ln) for ln in tex_block.split("\n") if not re.match(r"^\s*%", ln))
    m = re.search(r"\\toprule\b(.*?)\\midrule\b(.*?)\\bottomrule\b", no_cmt, re.S)
    rows = lambda seg: [_scan_tex_table(r, by_row=False) for r in _scan_tex_table(seg, by_row=True)]
    return (rows(m.group(1)), rows(m.group(2)), no_cmt) if m else ([], [], no_cmt)


def conv_list_items(lines: list[str], spec: SyncSpec, *, is_tex: bool) -> list[tuple[str, str]]:
    groups, in_eq = [], False
    item_re = re.compile(r"^\s*\\item(?:\s+|$)(.*)$") if is_tex else re.compile(r"^-\s+(.*)$")
    for ln in lines:
        if is_tex and re.match(r"^\s*\\begin\{equation\*?\}", ln):
            in_eq = True
        elif not is_tex and FENCE_OPEN.match(ln.strip()):
            in_eq = not in_eq; groups[-1].append(ln); continue
        (groups.append([ln]) if (not in_eq and item_re.match(ln)) else (groups[-1].append(ln) if groups else None))
        in_eq = False if (is_tex and re.match(r"^\s*\\end\{equation\*?\}", ln)) else in_eq
    res: list[tuple[str, str]] = []
    for grp in groups:
        m0 = item_re.match(grp[0])
        seq, out_l, k = [m0.group(1) if m0 else grp[0], *grp[1:]], [], 0
        while k < len(seq):
            if is_tex and (em := re.match(r"^\s*\\begin\{(equation\*?)\}(.*)$", seq[k])):
                lab, eb, k = _cmd_arg(strip_tex_comment(em.group(2)), r"\label"), [], k + 1
                while k < len(seq) and not re.match(r"^\s*\\end\{equation\*?\}", seq[k]):
                    eb.extend([strip_tex_comment(seq[k])] if not re.match(r"^\s*%", seq[k]) else []); k += 1
                out_l.append((f"$$ {{#{lab}}}\n" if lab else "$$\n") + "\n".join(eb) + "\n$$")
            elif not is_tex and (fm := FENCE_OPEN.match(seq[k].strip())):
                lab, eb, k = fm.group(1), [], k + 1
                while k < len(seq) and not FENCE_OPEN.match(seq[k].strip()):
                    eb.append(seq[k]); k += 1
                tag = f"equation}}\\label{{{lab}" if lab else "equation*"
                out_l.append(f"\\begin{{{tag}}}\n" + "\n".join(eb) + f"\n\\end{{{'equation' if lab else 'equation*'}}}")
            elif not (is_tex and re.match(r"^\s*%", seq[k])):
                conv = tex_inline_to_md(seq[k] if k == 0 else seq[k].strip(), spec) if is_tex else md_inline_to_tex(seq[k], spec)
                out_l.append((f"- {conv}" if is_tex else rf"\item {conv}") if k == 0 else conv)
            k += 1
        res.append(("\n".join(grp), "\n".join(out_l)))
    return res


def parse_tex_units(tex: str, spec: SyncSpec = KALMAN_SPEC) -> list[Unit]:
    if not tex:
        return []
    lines = tex.split("\n")[:-1] if tex.endswith("\n") else tex.split("\n")
    auto_map, num_map = dict(spec.auto_envs), dict(spec.num_envs)
    all_envs = set(auto_map) | set(num_map) | {spec.proof_env[0]}
    st_re = re.compile(r"^\\(?:section\*?|subsection|subsubsection|htdfig|htdfntext)\s*\{|^\\(?:begin|end)\{(?:equation\*?|itemize|htdtable|table|" + "|".join(all_envs) + r")\}")
    is_st = lambda ln: bool(re.match(r"^\s*%\s*<!--.*-->\s*$", ln) or strip_tex_comment(ln).strip() == spec.bib_tex or st_re.match(strip_tex_comment(ln).strip()))
    units, cmts, saw_blank, i, n = [], [], False, 0, len(lines)
    while i < n:
        if not lines[i].strip() or (re.match(r"^\s*%", lines[i]) and not re.match(r"^\s*%\s*<!--.*-->\s*$", lines[i])):
            saw_blank = True if not lines[i].strip() else saw_blank
            cmts.extend([lines[i]] if (cmts or lines[i].strip()) else [])
            i += 1; continue
        if units:
            units[-1].trailing_sep = "\n\n" if saw_blank else "\n"
        lead, cmts, saw_blank, ln_no, raw_ln, s = ("\n".join(cmts) + "\n" if cmts else ""), [], False, i + 1, lines[i], strip_tex_comment(lines[i]).strip()
        add = lambda knd, md_s, tex_s, meta="": units.append(Unit(knd, md_s, tex_s, leading_comments=lead, line=ln_no, meta=meta))
        if mm := re.match(r"^\s*%\s*(<!--.*-->)\s*$", raw_ln):
            add("marker", mm.group(1), raw_ln); i += 1
        elif s == spec.bib_tex or (s.startswith(r"\section*{") and grab_braced(s, 9)):
            r1 = grab_braced(s, 9) if s != spec.bib_tex else None
            add("bib" if s == spec.bib_tex else "p_h2", "<!--REFS-->" if s == spec.bib_tex else f'<p class="h2">{tex_inline_to_md(r1[0] if r1 else "", spec)}</p>', raw_ln); i += 1
        elif sm := re.match(r"^\\(section|subsection|subsubsection)\s*\{", s):
            r1 = grab_braced(s, sm.end() - 1)
            title, lab = (r1[0], _cmd_arg(s[r1[1]:], r"\label")) if r1 else ("", "")
            add("heading", f"{'#' * _LV_BY_SEC[sm.group(1)]} {tex_inline_to_md(title, spec)}" + (f" {{#{lab}}}" if lab else ""), raw_ln, lab); i += 1
        elif s.startswith((r"\htdfig", r"\htdfntext")):
            j, acc = i, raw_ln
            while j + 1 < n and acc.count("{") > acc.count("}"):
                j += 1; acc += "\n" + lines[j]
            args = _grab_seq("\n".join(strip_tex_comment(x) for x in acc.split("\n")), 3 if s.startswith(r"\htdfig") else 2)
            if s.startswith(r"\htdfig"):
                add("figure", f"![{tex_inline_to_md(args[2], spec)}]({args[0]})" + (f"{{#{args[1]}}}" if args[1] else ""), acc, args[1])
            else:
                add("footnote_def", f"[^{args[0]}]: {tex_inline_to_md(args[1], spec)}", acc, args[0])
            i = j + 1
        elif em := re.match(r"^\\begin\{(equation\*?|itemize|htdtable|table)\}", s):
            bname = em.group(1)
            end_i = next((k for k in range(i + 1, n) if strip_tex_comment(lines[k]).strip().startswith(rf"\end{{{bname}}}")), n - 1)
            raw_blk = "\n".join(lines[i : end_i + 1])
            if bname.startswith("equation"):
                lab, b_l = _cmd_arg(s[em.end():], r"\label"), lines[i + 1 : end_i]
                if not lab and b_l and re.match(r"^\s*\\label\{[^}]+\}\s*$", strip_tex_comment(b_l[0])):
                    lab, b_l = _cmd_arg(b_l[0], r"\label"), b_l[1:]
                body = "\n".join(strip_tex_comment(x) for x in b_l if not re.match(r"^\s*%", x))
                add("equation", (f"$$ {{#{lab}}}\n" if lab else "$$\n") + body + "\n$$", raw_blk, lab)
            elif bname == "itemize":
                add("list", "\n".join(m for _, m in conv_list_items(lines[i + 1 : end_i], spec, is_tex=True)), raw_blk)
            elif bname == "htdtable":
                hr, br, _ = _tex_table_parts(raw_blk)
                h_md = [tex_inline_to_md(c, spec) for c in (hr[0] if hr else [])]
                add("pipe_table", "\n".join(["| " + " | ".join(h_md) + " |", "| " + " | ".join("---" for _ in h_md) + " |", *("| " + " | ".join(tex_inline_to_md(c, spec) for c in r) + " |" for r in br)]), raw_blk)
            else:
                hr, br, no_cmt = _tex_table_parts(raw_blk)
                cap_md, lab = tex_inline_to_md(_cmd_arg(no_cmt, r"\caption"), spec), _cmd_arg(no_cmt, r"\label")
                thead = "".join("<tr>" + "".join(f"<th>{tex_inline_to_md(c, spec)}</th>" for c in r) + "</tr>" for r in hr)
                tbody = "\n".join("<tr>" + "".join(f"<td>{tex_inline_to_md(c, spec)}</td>" for c in r) + "</tr>" for r in br)
                add("html_table", f'<figure class="tbl" data-label="{lab}">\n<figcaption>{cap_md}</figcaption>\n<table>\n<thead>{thead}</thead>\n<tbody>\n{tbody}\n</tbody>\n</table>\n</figure>', raw_blk, lab)
            i = end_i + 1
        elif bm := re.match(r"^\\begin\{(" + "|".join(all_envs) + r")\}((?:.|\s)*)$", s):
            ename, rest = bm.group(1), bm.group(2).strip()
            if ename == spec.proof_env[0]:
                br = grab_bracketed(rest, 0) if rest.startswith("[") else None
                md = f"::: {spec.proof_env[1]}" + (f" {tex_inline_to_md(br[0], spec)}" if br and br[0] else "")
            else:
                nr = grab_braced(rest, 0) if (ename in num_map and rest.startswith("{")) else None
                num_s, r2 = (nr[0], rest[nr[1]:].lstrip()) if nr else ("", rest)
                br = grab_bracketed(r2, 0) if r2.startswith("[") else None
                lab = _cmd_arg(r2[br[1]:].lstrip() if br else r2, r"\label")
                attr = f" {{#{lab} num={num_s}}}" if num_s else (f" {{#{lab}}}" if lab else "")
                md = f"::: {num_map.get(ename) or auto_map[ename]}{attr}" + (f" {tex_inline_to_md(br[0], spec)}" if br and br[0] else "")
            add("env_open", md, raw_ln, ename); i += 1
        elif cm := re.match(r"^\\end\{(" + "|".join(all_envs) + r")\}\s*$", s):
            add("env_close", ":::", raw_ln, cm.group(1)); i += 1
        else:
            j = i + 1
            while j < n and lines[j].strip() and not is_st(lines[j]):
                if re.match(r"^\s*%", lines[j]):
                    k = next((x for x in range(j + 1, n) if not (re.match(r"^\s*%", lines[x]) and not re.match(r"^\s*%\s*<!--.*-->\s*$", lines[x]))), n)
                    if k >= n or not lines[k].strip() or is_st(lines[k]):
                        break
                j += 1
            raw_p = "\n".join(lines[i:j])
            add("para", tex_inline_to_md(raw_p, spec), raw_p); i = j
    return units


def parse_md_units(md: str, spec: SyncSpec = KALMAN_SPEC) -> list[Unit]:
    if not md:
        return []
    lines = md.split("\n")[:-1] if md.endswith("\n") else md.split("\n")
    auto_rev, num_rev = {k: e for e, k in spec.auto_envs}, {k: e for e, k in spec.num_envs}
    units, env_stack, saw_blank, i, n = [], [], False, 0, len(lines)
    is_st = lambda idx: bool(
        lines[idx].strip() == ":::" or FENCE_OPEN.match(lines[idx].strip()) or _P_H2_RE.match(lines[idx].strip())
        or re.match(r"^<!--.*-->$", lines[idx].strip()) or (idx + 1 < n and lines[idx].lstrip().startswith("|") and PIPE_SEP.match(lines[idx + 1]))
        or HEAD.match(lines[idx]) or BOX_OPEN.match(lines[idx]) or _MD_FIG_RE.match(lines[idx])
        or FOOTNOTE_DEF.match(lines[idx].strip()) or re.match(r"^-\s+|^<(?:figure|table|div)", lines[idx])
    )
    while i < n:
        if not lines[i].strip():
            saw_blank, i = True, i + 1; continue
        if units:
            units[-1].trailing_sep = "\n\n" if saw_blank else "\n"
        saw_blank, ln_no, raw_ln, st = False, i + 1, lines[i], lines[i].strip()
        add = lambda knd, md_s, tex_s, meta="": units.append(Unit(knd, md_s, tex_s, line=ln_no, meta=meta))
        if st == "<!--REFS-->" or re.match(r"^<!--.*-->$", st):
            add("bib" if st == "<!--REFS-->" else "marker", raw_ln, spec.bib_tex if st == "<!--REFS-->" else f"% {st}"); i += 1
        elif pm := _P_H2_RE.match(st):
            add("p_h2", raw_ln, rf"\section*{{{md_inline_to_tex(pm.group(1), spec)}}}"); i += 1
        elif raw_ln.startswith('<figure class="tbl"'):
            j = next((k for k in range(i + 1, n) if "</figure>" in lines[k]), n - 1)
            blk = "\n".join(lines[i : j + 1])
            lab = m.group(1) if (m := re.search(r'data-label="([^"]+)"', blk)) else ""
            cap = md_inline_to_tex(_tag_inner("figcaption", blk), spec)
            ths = [md_inline_to_tex(c, spec) for c in re.findall(r"<th[^>]*>(.*?)</th>", _tag_inner("thead", blk), re.S)]
            trs = [" & ".join(md_inline_to_tex(c, spec) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)) + r" \\" for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", _tag_inner("tbody", blk), re.S)]
            cspec = "cXX" if len(ths) == 3 else ("l" * max(0, len(ths) - 1) + "X")
            add("html_table", blk, "\n".join([r"\begin{table}[htbp]", r"\centering", rf"\caption{{{cap}}}\label{{{lab}}}", rf"\begin{{tabularx}}{{\textwidth}}{{{cspec}}}", r"\toprule", " & ".join(ths) + r" \\", r"\midrule", *trs, r"\bottomrule", r"\end{tabularx}", r"\end{table}"]), lab); i = j + 1
        elif fm := FENCE_OPEN.match(st):
            j, cm = i + 1, None
            while j < n and not (cm := FENCE_OPEN.match(lines[j].strip())):
                j += 1
            end_i, lab = min(j, n - 1), fm.group(1) or (cm.group(1) if cm else "") or ""
            tag = f"equation}}\\label{{{lab}" if lab else "equation*"
            add("equation", "\n".join(lines[i : end_i + 1]), f"\\begin{{{tag}}}\n" + "\n".join(lines[i + 1 : end_i]) + f"\n\\end{{{'equation' if lab else 'equation*'}}}", lab); i = end_i + 1
        elif st == ":::":
            ename = env_stack.pop() if env_stack else "unknown"
            add("env_close", raw_ln, rf"\end{{{ename}}}", ename); i += 1
        elif bm := BOX_OPEN.match(raw_ln):
            kind, lab, raw_num, title = bm.group(1), bm.group(2) or "", (bm.group(3) or "").strip("\"'"), bm.group(4).strip()
            t_opt, l_opt = (f"[{md_inline_to_tex(title, spec)}]" if title else ""), (rf"\label{{{lab}}}" if lab else "")
            ename = spec.proof_env[0] if kind in (spec.proof_env[1], spec.proof_env[0]) else (num_rev.get(kind, "theoremn") if raw_num else auto_rev.get(kind, "theorem"))
            tex_s = rf"\begin{{{ename}}}{t_opt}" if ename == spec.proof_env[0] else rf"\begin{{{ename}}}" + (f"{{{raw_num}}}" if raw_num else "") + f"{t_opt}{l_opt}"
            env_stack.append(ename); add("env_open", raw_ln, tex_s, ename); i += 1
        elif fnm := FOOTNOTE_DEF.match(st):
            fid, fparts, j = fnm.group(1), [fnm.group(2).strip()], i + 1
            while j < n and lines[j].startswith(("  ", "\t")) and not FOOTNOTE_DEF.match(lines[j].strip()):
                fparts.append(lines[j].strip()); j += 1
            add("footnote_def", "\n".join(lines[i:j]), rf"\htdfntext{{{fid}}}{{{md_inline_to_tex(' '.join(fparts), spec)}}}", fid); i = j
        elif i + 1 < n and raw_ln.lstrip().startswith("|") and PIPE_SEP.match(lines[i + 1]):
            j = next((k for k in range(i + 2, n) if not lines[k].lstrip().startswith("|")), n)
            h_t = [md_inline_to_tex(c, spec) for c in split_pipe_cells(lines[i])]
            b_t = [" & ".join(md_inline_to_tex(c, spec) for c in split_pipe_cells(r)) + r" \\" for r in lines[i + 2 : j]]
            add("pipe_table", "\n".join(lines[i:j]), "\n".join([rf"\begin{{htdtable}}{{{spec.colspec_for(len(h_t))}}}", r"\toprule", " & ".join(h_t) + r" \\", r"\midrule", *b_t, r"\bottomrule", r"\end{htdtable}"])); i = j
        elif hm := HEAD.match(raw_ln):
            add("heading", raw_ln, rf"\{_SEC_LV[len(hm.group(1))]}{{{md_inline_to_tex(hm.group(2), spec)}}}" + (rf"\label{{{hm.group(3)}}}" if hm.group(3) else ""), hm.group(3) or ""); i += 1
        elif fgm := _MD_FIG_RE.match(raw_ln):
            add("figure", raw_ln, rf"\htdfig{{{fgm.group(2).strip()}}}{{{fgm.group(3) or ''}}}{{{md_inline_to_tex(fgm.group(1), spec)}}}", fgm.group(3) or ""); i += 1
        elif re.match(r"^-\s+|^<(?:figure|table|div)", raw_ln):
            j = next((k for k in range(i + 1, n) if not lines[k].strip()), n)
            is_l = raw_ln.startswith("-")
            add("list" if is_l else "html_table", "\n".join(lines[i:j]), (r"\begin{itemize}" + "\n" + "\n".join(t for _, t in conv_list_items(lines[i:j], spec, is_tex=False)) + "\n" + r"\end{itemize}") if is_l else "", "" if is_l else "raw"); i = j
        else:
            j = next((k for k in range(i + 1, n) if not lines[k].strip() or is_st(k)), n)
            add("para", "\n".join(lines[i:j]), md_inline_to_tex("\n".join(lines[i:j]), spec)); i = j
    return units


def tex_to_md(tex: str, spec: SyncSpec = KALMAN_SPEC) -> str:
    return ("".join(u.md_text + u.trailing_sep for u in parse_tex_units(tex, spec)) + ("\n" if tex.endswith("\n") else "")) if tex else ""


def md_to_tex(md: str, spec: SyncSpec = KALMAN_SPEC) -> str:
    return ("".join(u.leading_comments + u.tex_text + u.trailing_sep for u in parse_md_units(md, spec)) + ("\n" if md.endswith("\n") else "")) if md else ""
