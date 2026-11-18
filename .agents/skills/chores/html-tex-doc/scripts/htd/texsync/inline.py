"""行内双向转换（F_inline / G_inline）、花括号配对解析与按句最小替换。"""
from __future__ import annotations

from dataclasses import dataclass
import difflib
import re


@dataclass(frozen=True)
class SyncSpec:
    ref_templates: tuple[tuple[str, str, str], ...] = (
        ("eq:", r"式~\eqref{", ""), ("thm:", r"定理~\ref{", ""), ("cor:", r"推论~\ref{", ""),
        ("prob:", r"问题~\ref{", ""), ("rem:", r"评注~\ref{", ""), ("ex:", r"算例~\ref{", ""),
        ("fig:", r"图~\ref{", ""), ("tab:", r"表~\ref{", ""), ("sec:", r"第~\ref{", "~节"),
    )
    auto_envs: tuple[tuple[str, str], ...] = (("theorem", "定理"), ("corollary", "推论"), ("example", "算例"))
    num_envs: tuple[tuple[str, str], ...] = (("theoremn", "定理"), ("problemn", "问题"), ("remarkn", "评注"))
    proof_env: tuple[str, str] = ("proof", "证明")
    bib_tex: str = r"\bibliography{html/src/refs}"
    colspecs: tuple[tuple[int, str], ...] = ((2, "lX"), (3, r"p{0.24\textwidth}p{0.19\textwidth}X"))

    def colspec_for(self, ncols: int) -> str:
        return dict(self.colspecs).get(ncols, "l" * max(0, ncols - 1) + "X")


KALMAN_SPEC = SyncSpec()
_PLACEHOLDER_RE = re.compile(r"\x00S(\d+)\x00")
_MD_XREF_RE = re.compile(r"\{@([\w:.-]+)(?:\|([^}\n]+))?\}")
_CLOSERS = frozenset("”’）)】』》\"'")
_TEX_CMDS = (
    (r"\eqref{", "({{@{0}|n}})", False), (r"\ref{", "{{@{0}|n}}", False),
    (r"\cite{", "[@{0}]", False), (r"\htdfnmark{", "[^{0}]", False),
    (r"\textbf{", "**{0}**", True), (r"\emph{", "*{0}*", True),
)
_MD_PATS = (
    (re.compile(r"\(\{@(eq:[\w:.-]+)\|n\}\)"), r"\eqref{{{0}}}", False),
    (re.compile(r"\[@([^\]]+)\]"), r"\cite{{{0}}}", False),
    (re.compile(r"\[\^([\w-]+)\](?!:)"), r"\htdfnmark{{{0}}}", False),
    (re.compile(r"\*\*(.+?)\*\*", re.S), r"\textbf{{{0}}}", True),
)


def grab_braced(s: str, pos: int) -> tuple[str, int] | None:
    if pos < 0 or pos >= len(s) or s[pos] != "{":
        return None
    depth, i = 1, pos + 1
    while i < len(s) and depth > 0:
        if s[i] == "\\" and i + 1 < len(s):
            i += 2; continue
        depth += 1 if s[i] == "{" else (-1 if s[i] == "}" else 0)
        i += 1
    return (s[pos + 1 : i - 1], i) if depth == 0 else None


def grab_bracketed(s: str, pos: int) -> tuple[str, int] | None:
    if pos < 0 or pos >= len(s) or s[pos] != "[":
        return None
    b_d, c_d, i = 1, 0, pos + 1
    while i < len(s) and b_d > 0:
        if s[i] == "\\" and i + 1 < len(s):
            i += 2; continue
        if s[i] in "{}":
            c_d = max(0, c_d + (1 if s[i] == "{" else -1))
        elif c_d == 0 and s[i] in "[]":
            b_d += 1 if s[i] == "[" else -1
        i += 1
    return (s[pos + 1 : i - 1], i) if b_d == 0 else None


def strip_tex_comment(line: str) -> str:
    i = 0
    while i < len(line):
        if line.startswith(r"\texttt{", i) and (res := grab_braced(line, i + 7)):
            i = res[1]
        elif line[i] == "\\" and i + 1 < len(line):
            i += 2
        elif line[i] == "%":
            return line[:i].rstrip(" \t")
        else:
            i += 1
    return line


def _stash_protected(s: str, *, is_tex: bool) -> tuple[str, list[str]]:
    stash, buf, i, n = [], [], 0, len(s)
    while i < n:
        if is_tex and s.startswith(r"\texttt{", i) and (res := grab_braced(s, i + 7)):
            stash.append(f"`{res[0]}`"); buf.append(f"\x00S{len(stash) - 1}\x00"); i = res[1]
        elif not is_tex and s[i] == "`" and (j := s.find("`", i + 1)) != -1 and "\n" not in s[i + 1 : j]:
            stash.append(rf"\texttt{{{s[i + 1 : j]}}}"); buf.append(f"\x00S{len(stash) - 1}\x00"); i = j + 1
        elif s[i] == "\\" and i + 1 < n and s[i + 1] in ("$%&_#{}\\" if is_tex else "$"):
            buf.append(s[i : i + 2]); i += 2
        elif s[i] == "$" and (i + 1 >= n or s[i + 1] != "$"):
            j = i + 1
            while j < n and s[j] != "$":
                j += 2 if (s[j] == "\\" and j + 1 < n) else 1
            if j < n:
                stash.append(s[i : j + 1]); buf.append(f"\x00S{len(stash) - 1}\x00"); i = j + 1
            else:
                buf.append(s[i]); i += 1
        else:
            buf.append(s[i]); i += 1
    return "".join(buf), stash


def _tex_body_to_md(text: str, spec: SyncSpec) -> str:
    out, i, n = [], 0, len(text)
    while i < n:
        ref_hit = next(
            ((res[0], res[1] + len(sf)) for pf, op, sf in spec.ref_templates
             if not (i > 0 and op.startswith("式~") and text[i - 1] in "公等原上下形系达开近根定通")
             and text.startswith(op, i) and (res := grab_braced(text, i + len(op) - 1)) and res[0].startswith(pf) and text.startswith(sf, res[1])),
            None,
        )
        if ref_hit:
            out.append(f"{{@{ref_hit[0]}}}"); i = ref_hit[1]
        elif text.startswith(r"\hyperref[", i) and (br := grab_bracketed(text, i + 9)) and br[1] < n and text[br[1]] == "{" and (cr := grab_braced(text, br[1])):
            out.append(f"{{@{br[0]}|{_tex_body_to_md(cr[0], spec)}}}"); i = cr[1]
        elif hit := next(((fmt, rec, cr) for cmd, fmt, rec in _TEX_CMDS if text.startswith(cmd, i) and (cr := grab_braced(text, i + len(cmd) - 1))), None):
            out.append(hit[0].format(_tex_body_to_md(hit[2][0], spec) if hit[1] else hit[2][0])); i = hit[2][1]
        elif text.startswith((r"\_", r"\&", r"\%", r"\#"), i):
            out.append(text[i + 1]); i += 2
        elif text.startswith(r"\~{}", i):
            out.append("~"); i += 4
        else:
            out.append(" " if text[i] == "~" else text[i]); i += 1
    return "".join(out)


def tex_inline_to_md(s: str, spec: SyncSpec = KALMAN_SPEC) -> str:
    lines = [ln for ln in s.split("\n") if not re.match(r"^\s*%", ln)] if "\n" in s else [s]
    protected, stash = _stash_protected("\n".join(strip_tex_comment(ln) for ln in lines), is_tex=True)
    return _PLACEHOLDER_RE.sub(lambda m: stash[int(m.group(1))], _tex_body_to_md(protected, spec))


def _find_single_star(text: str, start: int) -> int:
    j = start
    while j < len(text) and text[j] != "\n":
        if text.startswith("**", j):
            eb = text.find("**", j + 2)
            j = eb + 2 if eb != -1 else j + 2
        elif text[j] == "*":
            return j
        else:
            j += 1
    return -1


def _md_body_to_tex(text: str, spec: SyncSpec) -> str:
    out, i, n = [], 0, len(text)
    while i < n:
        if hit := next(((m, fmt, rec) for rx, fmt, rec in _MD_PATS if (m := rx.match(text, i))), None):
            m, fmt, rec = hit
            out.append(fmt.format(_md_body_to_tex(m.group(1), spec) if rec else m.group(1))); i = m.end()
        elif m := _MD_XREF_RE.match(text, i):
            key, mod = m.group(1), m.group(2)
            if mod is None:
                out.append(next((f"{op}{key}}}{sf}" for pf, op, sf in spec.ref_templates if key.startswith(pf)), rf"\ref{{{key}}}"))
            else:
                out.append(rf"\ref{{{key}}}" if mod == "n" else rf"\hyperref[{key}]{{{_md_body_to_tex(mod, spec)}}}")
            i = m.end()
        elif text[i] == "*" and (i == 0 or text[i - 1] != "*") and (j := _find_single_star(text, i + 1)) > i + 1:
            out.append(rf"\emph{{{_md_body_to_tex(text[i + 1 : j], spec)}}}"); i = j + 1
        else:
            out.append(("\\" + text[i]) if text[i] in "_&%#" else text[i]); i += 1
    return "".join(out)


def md_inline_to_tex(s: str, spec: SyncSpec = KALMAN_SPEC) -> str:
    protected, stash = _stash_protected(s, is_tex=False)
    return _PLACEHOLDER_RE.sub(lambda m: stash[int(m.group(1))], _md_body_to_tex(protected, spec))


def split_sentences(text: str, *, is_tex: bool = False) -> list[str]:
    if not text:
        return []
    sents, start, i, c_d, b_d, in_math, in_code, n = [], 0, 0, 0, 0, False, False, len(text)
    while i < n:
        ch = text[i]
        if ch == "\\" and i + 1 < n and not in_code:
            i += 2; continue
        if is_tex and not in_math and not in_code and ch == "%":
            nl = text.find("\n", i)
            i = n if nl == -1 else nl + 1; continue
        if not in_math and ch == "`":
            in_code, i = not in_code, i + 1; continue
        if not in_code and ch == "$" and (i + 1 >= n or text[i + 1] != "$"):
            in_math, i = not in_math, i + 1; continue
        if not (in_math or in_code):
            if not is_tex and c_d == 0 and b_d == 0 and ch == "*":
                if text.startswith("**", i) and (eb := text.find("**", i + 2)) != -1:
                    i = eb + 2; continue
                if (es := _find_single_star(text, i + 1)) > i + 1:
                    i = es + 1; continue
            if ch in "{}":
                c_d = max(0, c_d + (1 if ch == "{" else -1))
            elif ch in "[]":
                b_d = max(0, b_d + (1 if ch == "[" else -1))
            elif c_d == 0 and b_d == 0 and ((cjk := ch in "。！？；") or (ch in ".!?" and (i + 1 == n or text[i + 1] != "."))):
                j = i + 1
                while j < n and text[j] in _CLOSERS:
                    j += 1
                if cjk or j == n or text[j] in " \t\n" or (is_tex and text[j] == "%"):
                    if is_tex and (cm := re.match(r"[ \t]*%[^\n]*", text[j:])):
                        j += cm.end()
                    if ws := re.match(r"[ \t]*\n?", text[j:]):
                        j += ws.end()
                    sents.append(text[start:j]); start = i = j; continue
        i += 1
    return [*sents, text[start:]] if start < n else sents


def patch_paragraph_minimal(orig_tex: str, new_md: str, spec: SyncSpec = KALMAN_SPEC) -> str:
    if tex_inline_to_md(orig_tex, spec) == new_md:
        return orig_tex
    tex_sents, md_sents = split_sentences(orig_tex, is_tex=True), split_sentences(new_md, is_tex=False)
    sm = difflib.SequenceMatcher(None, [tex_inline_to_md(s, spec) for s in tex_sents], md_sents, autojunk=False)
    parts = [s for tag, i1, i2, j1, j2 in sm.get_opcodes() for s in (tex_sents[i1:i2] if tag == "equal" else ([md_inline_to_tex(x, spec) for x in md_sents[j1:j2]] if tag in ("replace", "insert") else []))]
    cand = "".join(parts)
    return cand if tex_inline_to_md(cand, spec) == new_md else md_inline_to_tex(new_md, spec)
