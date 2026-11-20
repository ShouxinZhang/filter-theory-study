"""块级双向语法编解码（parse_tex_units / parse_md_units / tex_to_md / md_to_tex）。"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re
from ..mdblocks import split_pipe_cells
from ..mdsyntax import BOX_OPEN, FENCE_OPEN, FOOTNOTE_DEF, HEAD, PIPE_SEP
from .floats import (
    cmd_arg, md_figure_block_to_unit_fields, tex_algorithm_to_md,
    tex_figure_to_md, tex_htdtable_to_md, tex_table_to_md,
)
from .inline import KALMAN_SPEC, SyncSpec, grab_braced, grab_bracketed, md_inline_to_tex, strip_tex_comment, tex_inline_to_md

_MD_FIG_RE = re.compile(r"^!\[(.*)\]\(([^()\s]+)\)\s*(?:\{#([^}]+)\})?\s*$")
_P_H2_RE = re.compile(r'^<p class="h2">(.*)</p>\s*$')
_TEX_INPUT_MD_RE = re.compile(r"^<!--tex-input:\s*(.+?)\s*-->$")


@dataclass
class Unit:
    kind: str; md_text: str; tex_text: str; trailing_sep: str = ""; leading_comments: str = ""; line: int = 1; meta: str = ""


TexUnit = MdUnit = Unit


def _grab_seq(text: str, count: int) -> list[str]:
    pos, out = text.find("{"), []
    for _ in range(count):
        if pos == -1 or not (res := grab_braced(text, pos)):
            return [""] * count
        out.append(res[0]); pos = text.find("{", res[1])
    return out


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
                lab, eb, k = cmd_arg(strip_tex_comment(em.group(2)), r"\label"), [], k + 1
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


def parse_tex_units(tex: str, spec: SyncSpec = KALMAN_SPEC, *, float_inputs: Mapping[str, Unit] | None = None) -> list[Unit]:
    if not tex:
        return []
    lines = tex.split("\n")[:-1] if tex.endswith("\n") else tex.split("\n")
    auto_map, num_map = dict(spec.auto_envs), dict(spec.num_envs)
    all_envs = set(auto_map) | set(num_map) | {spec.proof_env[0]}
    lv_by_cmd = {c: idx + 1 for idx, c in enumerate(spec.heading_cmds)}
    h_pat = "|".join(map(re.escape, spec.heading_cmds))
    h_re = re.compile(rf"^\\({h_pat})\s*(?:\[|\{{)")
    h_star = f"\\{spec.heading_cmds[0]}*{{"
    st_re = re.compile(
        rf"^\\(?:{h_pat})\*?\s*(?:\[|\{{)|^\\(?:htdfig|htdfntext|input)\s*\{{|"
        r"^\\(?:begin|end)\{(?:equation\*?|itemize|htdtable|table\*?|figure\*?|algorithm|" + "|".join(map(re.escape, all_envs)) + r")\}"
    )
    is_st = lambda ln: bool(re.match(r"^\s*%\s*<!--.*-->\s*$", ln) or strip_tex_comment(ln).strip() == spec.bib_tex or st_re.match(strip_tex_comment(ln).strip()))
    units, cmts, saw_blank, alg_idx, i, n = [], [], False, 0, 0, len(lines)
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
        elif s == spec.bib_tex or (s.startswith(h_star) and grab_braced(s, len(h_star) - 1)):
            r1 = grab_braced(s, len(h_star) - 1) if s != spec.bib_tex else None
            add("bib" if s == spec.bib_tex else "p_h2", "<!--REFS-->" if s == spec.bib_tex else f'<p class="h2">{tex_inline_to_md(r1[0] if r1 else "", spec)}</p>', raw_ln); i += 1
        elif sm := h_re.match(s):
            cmd, pos = sm.group(1), sm.end() - 1
            if s[pos] == "[" and (br0 := grab_bracketed(s, pos)):
                pos = br0[1] + len(s[br0[1]:]) - len(s[br0[1]:].lstrip())
            r1 = grab_braced(s, pos) if pos < len(s) and s[pos] == "{" else None
            title, rest = (r1[0], s[r1[1]:].lstrip()) if r1 else ("", "")
            if rest.startswith("[") and (br1 := grab_bracketed(rest, 0)):
                rest = rest[br1[1]:].lstrip()
            lab = cmd_arg(rest, r"\label")
            add("heading", f"{'#' * lv_by_cmd[cmd]} {tex_inline_to_md(title, spec)}" + (f" {{#{lab}}}" if lab else ""), raw_ln, lab); i += 1
        elif (im := re.match(r"^\\input\s*\{", s)) and (ir := grab_braced(s, im.end() - 1)) and not s[ir[1]:].strip():
            rel = ir[0].strip()
            if float_inputs and rel in float_inputs:
                fu = float_inputs[rel]
                add(fu.kind, fu.md_text, raw_ln, fu.meta)
            else:
                add("tex_input", f"<!--tex-input: {rel}-->", raw_ln, rel)
            i += 1
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
        elif em := re.match(r"^\\begin\{(equation\*?|itemize|htdtable|table\*?|figure\*?|algorithm)\}", s):
            bname = em.group(1)
            end_i = next((k for k in range(i + 1, n) if strip_tex_comment(lines[k]).strip().startswith(rf"\end{{{bname}}}")), n - 1)
            raw_blk = "\n".join(lines[i : end_i + 1])
            if bname.startswith("equation"):
                lab, b_l = cmd_arg(s[em.end():], r"\label"), lines[i + 1 : end_i]
                if not lab and b_l and re.match(r"^\s*\\label\{[^}]+\}\s*$", strip_tex_comment(b_l[0])):
                    lab, b_l = cmd_arg(b_l[0], r"\label"), b_l[1:]
                body = "\n".join(strip_tex_comment(x) for x in b_l if not re.match(r"^\s*%", x))
                add("equation", (f"$$ {{#{lab}}}\n" if lab else "$$\n") + body + "\n$$", raw_blk, lab)
            elif bname == "itemize":
                add("list", "\n".join(m for _, m in conv_list_items(lines[i + 1 : end_i], spec, is_tex=True)), raw_blk)
            elif bname == "htdtable":
                add("pipe_table", tex_htdtable_to_md(raw_blk, spec), raw_blk)
            elif bname.startswith("table"):
                md_s, lab = tex_table_to_md(raw_blk, spec)
                add("html_table", md_s, raw_blk, lab)
            elif bname.startswith("figure"):
                md_s, lab = tex_figure_to_md(raw_blk, spec)
                add("figure", md_s, raw_blk, lab)
            else:
                alg_idx += 1
                md_s, lab = tex_algorithm_to_md(raw_blk, spec, alg_idx)
                add("algorithm", md_s, raw_blk, lab)
            i = end_i + 1
        elif bm := re.match(r"^\\begin\{(" + "|".join(map(re.escape, all_envs)) + r")\}((?:.|\s)*)$", s):
            ename, rest = bm.group(1), bm.group(2).strip()
            if ename == spec.proof_env[0]:
                br = grab_bracketed(rest, 0) if rest.startswith("[") else None
                md = f"::: {spec.proof_env[1]}" + (f" {tex_inline_to_md(br[0], spec)}" if br and br[0] else "")
            else:
                nr = grab_braced(rest, 0) if (ename in num_map and rest.startswith("{")) else None
                num_s, r2 = (nr[0], rest[nr[1]:].lstrip()) if nr else ("", rest)
                br = grab_bracketed(r2, 0) if r2.startswith("[") else None
                lab = cmd_arg(r2[br[1]:].lstrip() if br else r2, r"\label")
                attr = f" {{#{lab} num={num_s}}}" if num_s else (f" {{#{lab}}}" if lab else "")
                md = f"::: {num_map.get(ename) or auto_map[ename]}{attr}" + (f" {tex_inline_to_md(br[0], spec)}" if br and br[0] else "")
            add("env_open", md, raw_ln, ename); i += 1
        elif cm := re.match(r"^\\end\{(" + "|".join(map(re.escape, all_envs)) + r")\}\s*$", s):
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
    auto_rev, num_rev = {k: e for e, k in reversed(spec.auto_envs)}, {k: e for e, k in reversed(spec.num_envs)}
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
        if st == "<!--REFS-->":
            add("bib", raw_ln, spec.bib_tex); i += 1
        elif tim := _TEX_INPUT_MD_RE.match(st):
            add("tex_input", raw_ln, rf"\input{{{tim.group(1)}}}", tim.group(1)); i += 1
        elif re.match(r"^<!--.*-->$", st):
            add("marker", raw_ln, f"% {st}"); i += 1
        elif pm := _P_H2_RE.match(st):
            add("p_h2", raw_ln, rf"\{spec.heading_cmds[0]}*{{{md_inline_to_tex(pm.group(1), spec)}}}"); i += 1
        elif raw_ln.startswith(('<figure class="tbl"', '<figure class="fig"', '<figure class="alg"')):
            j = next((k for k in range(i, n) if "</figure>" in lines[k]), n - 1)
            blk = "\n".join(lines[i : j + 1])
            knd, tex_s, lab = md_figure_block_to_unit_fields(blk, spec)
            add(knd, blk, tex_s, lab); i = j + 1
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
            cmd = spec.heading_cmds[min(len(hm.group(1)), 3) - 1]
            add("heading", raw_ln, rf"\{cmd}{{{md_inline_to_tex(hm.group(2), spec)}}}" + (rf"\label{{{hm.group(3)}}}" if hm.group(3) else ""), hm.group(3) or ""); i += 1
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


def tex_to_md(tex: str, spec: SyncSpec = KALMAN_SPEC, *, float_inputs: Mapping[str, Unit] | None = None) -> str:
    return ("".join(u.md_text + u.trailing_sep for u in parse_tex_units(tex, spec, float_inputs=float_inputs)) + ("\n" if tex.endswith("\n") else "")) if tex else ""


def md_to_tex(md: str, spec: SyncSpec = KALMAN_SPEC) -> str:
    return ("".join(u.leading_comments + u.tex_text + u.trailing_sep for u in parse_md_units(md, spec)) + ("\n" if md.endswith("\n") else "")) if md else ""
