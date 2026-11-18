"""最小差异回写引擎（patch_tex）、切片结构守卫（SyncPair）与导入/导出 CLI。"""
from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
import difflib
import os
from pathlib import Path
import re
import sys
import tempfile
from .codec import Unit, conv_list_items, parse_md_units, parse_tex_units, tex_to_md
from .inline import KALMAN_SPEC, SyncSpec, patch_paragraph_minimal

_MANUAL_KINDS = frozenset({"html_table", "figure", "env_open", "env_close"})


@dataclass
class PatchResult:
    ok: bool
    patched_tex: str
    diff_text: str
    manual_items: list[str]
    roundtrip_mismatch: str | None = None


@dataclass(frozen=True)
class SyncPair:
    tex_path: Path | str
    md_path: Path | str
    md_slice: tuple[str, str] | None = None
    expected_md_frame: tuple[str, str] | str | Path | None = None


def _desc_unit(u: Unit) -> str:
    names = {"html_table": "编号表格", "figure": "浮动图", "env_open": "环境开启", "env_close": "环境闭合"}
    return f"{names.get(u.kind, u.kind)} ({u.meta or u.md_text.splitlines()[0][:24]})"


def patch_list_minimal(orig_tex: str, new_md: str, spec: SyncSpec = KALMAN_SPEC) -> str:
    olines = orig_tex.split("\n")
    orig_items = conv_list_items(olines[1:-1], spec, is_tex=True)
    new_items = conv_list_items(new_md.split("\n"), spec, is_tex=False)
    ind = m.group(1) if (orig_items and (m := re.match(r"^(\s*)\\item", orig_items[0][0]))) else ""
    sm = difflib.SequenceMatcher(None, [m for _, m in orig_items], [m for m, _ in new_items], autojunk=False)
    out: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.extend(orig_items[k][0] for k in range(i1, i2))
        elif tag == "replace" and (i2 - i1) == (j2 - j1):
            for (ot, _), (nm, nt) in zip(orig_items[i1:i2], new_items[j1:j2]):
                if "\n" not in ot and "\n" not in nm and (om := re.match(r"^(\s*\\item\s+)(.*)$", ot)):
                    out.append(om.group(1) + patch_paragraph_minimal(om.group(2), re.sub(r"^-\s+", "", nm, count=1), spec))
                else:
                    out.append(ind + nt)
        elif tag in ("replace", "insert"):
            out.extend(ind + nt for _, nt in new_items[j1:j2])
    cand = f"{olines[0]}\n" + "\n".join(out) + f"\n{olines[-1]}"
    cand_md = "\n".join(m for _, m in conv_list_items(cand.split("\n")[1:-1], spec, is_tex=True))
    return cand if cand_md == new_md else (r"\begin{itemize}" + "\n" + "\n".join(t for _, t in new_items) + "\n" + r"\end{itemize}")


def _first_mismatch(rt_md: str, new_md: str, pfx: str, spec: SyncSpec) -> str:
    rt_u, nw_u = parse_md_units(rt_md, spec), parse_md_units(new_md, spec)
    for u1, u2 in zip(rt_u, nw_u):
        if (u1.kind, u1.md_text, u1.trailing_sep) != (u2.kind, u2.md_text, u2.trailing_sep):
            return f"{pfx}L{u2.line} 回写往返不一致: 期望 {u2.md_text[:40]!r}，实际 {u1.md_text[:40]!r}"
    ln = nw_u[min(len(rt_u), len(nw_u))].line if len(nw_u) > len(rt_u) and nw_u else (rt_u[-1].line if rt_u else 1)
    return f"{pfx}L{ln} 回写往返块数或末尾换行不一致 ({len(rt_u)} vs {len(nw_u)})"


def patch_tex(orig_tex: str, new_md: str, spec: SyncSpec = KALMAN_SPEC, filename: str = "") -> PatchResult:
    pfx = f"{filename}:" if filename else ""
    orig_u, new_u = parse_tex_units(orig_tex, spec), parse_md_units(new_md, spec)
    sm = difflib.SequenceMatcher(None, [(u.kind, u.md_text, u.meta) for u in orig_u], [(u.kind, u.md_text, u.meta) for u in new_u], autojunk=False)
    chunks: list[tuple[str, str, str]] = []
    manual: list[str] = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            chunks.extend((ou.leading_comments, ou.tex_text, nu.trailing_sep) for ou, nu in zip(orig_u[i1:i2], new_u[j1:j2]))
        elif tag == "delete":
            for ou in orig_u[i1:i2]:
                if ou.kind in _MANUAL_KINDS:
                    manual.append(f"{pfx}L{ou.line} 删除 {_desc_unit(ou)}，需人工处理")
                    chunks.append((ou.leading_comments, ou.tex_text, ou.trailing_sep or "\n\n"))
        elif tag == "insert":
            for nu in new_u[j1:j2]:
                if nu.kind in _MANUAL_KINDS:
                    manual.append(f"{pfx}L{nu.line} 新增 {_desc_unit(nu)}，需人工处理")
                else:
                    chunks.append(("", nu.tex_text, nu.trailing_sep))
        elif tag == "replace":
            osub, nsub = orig_u[i1:i2], new_u[j1:j2]
            if len(osub) == 1 and len(nsub) == 1 and osub[0].kind == nsub[0].kind and osub[0].kind in _MANUAL_KINDS:
                manual.append(f"{pfx}L{osub[0].line} 修改 {_desc_unit(osub[0])}，需人工处理")
                chunks.append((osub[0].leading_comments, osub[0].tex_text, nsub[0].trailing_sep))
                continue
            for ou in (u for u in osub if u.kind in _MANUAL_KINDS):
                manual.append(f"{pfx}L{ou.line} 修改或删除 {_desc_unit(ou)}，需人工处理")
                chunks.append((ou.leading_comments, ou.tex_text, ou.trailing_sep or "\n\n"))
            for nu in (u for u in nsub if u.kind in _MANUAL_KINDS):
                manual.append(f"{pfx}L{nu.line} 新增或修改 {_desc_unit(nu)}，需人工处理")
            ow, nw = [u for u in osub if u.kind not in _MANUAL_KINDS], [u for u in nsub if u.kind not in _MANUAL_KINDS]
            paired: dict[int, int] = {k: k for k in range(len(nw))} if len(ow) == len(nw) else {}
            if len(ow) != len(nw):
                used_o: set[int] = set()
                for ni, nu in enumerate(nw):
                    cands = [(difflib.SequenceMatcher(None, ou.md_text, nu.md_text, autojunk=False).ratio(), oi) for oi, ou in enumerate(ow) if oi not in used_o and ou.kind == nu.kind]
                    if cands and max(cands)[0] >= 0.35:
                        _, best_i = max(cands)
                        paired[ni] = best_i; used_o.add(best_i)
            for ni, nu in enumerate(nw):
                ou = ow[paired[ni]] if ni in paired else None
                body = patch_paragraph_minimal(ou.tex_text, nu.md_text, spec) if (ou and nu.kind == "para" and ou.kind == "para") else (patch_list_minimal(ou.tex_text, nu.md_text, spec) if (ou and nu.kind == "list" and ou.kind == "list") else nu.tex_text)
                chunks.append((ou.leading_comments if ou else "", body, nu.trailing_sep))

    raw_body = "".join(c[0] + c[1] + c[2] for c in chunks)
    patched = (raw_body + ("\n" if new_md.endswith("\n") else "")) if (raw_body or new_md) else ""
    lbl = filename or "tex"
    diff_txt = "".join(difflib.unified_diff(orig_tex.splitlines(keepends=True), patched.splitlines(keepends=True), fromfile=f"a/{lbl}", tofile=f"b/{lbl}"))
    rt_md = tex_to_md(patched, spec)
    mismatch = _first_mismatch(rt_md, new_md, pfx, spec) if rt_md != new_md else None
    return PatchResult(ok=(not manual and mismatch is None), patched_tex=patched, diff_text=diff_txt, manual_items=manual, roundtrip_mismatch=mismatch)


def _split_slice(text: str, md_slice: tuple[str, str]) -> tuple[str, str, str, str, str] | None:
    i0 = text.find(md_slice[0])
    if i0 == -1 or (i1 := text.find(md_slice[1], i0 + len(md_slice[0]))) == -1:
        return None
    s0, inner = i0 + len(md_slice[0]), text[i0 + len(md_slice[0]) : i1]
    lead, core = inner[: len(inner) - len(inner.lstrip("\n"))], inner.strip("\n")
    return text[:s0], lead, core, inner[len(lead) + len(core) :], text[i1:]


def _diff_line(a: str, b: str, base: int = 1) -> int:
    return next((base + k for k, (la, lb) in enumerate(zip(a.splitlines(), b.splitlines())) if la != lb), base + min(len(a.splitlines()), len(b.splitlines())))


def check_pair_export(pair: SyncPair, spec: SyncSpec = KALMAN_SPEC) -> PatchResult:
    tex_p, md_p = Path(pair.tex_path), Path(pair.md_path)
    orig_tex, raw_md = tex_p.read_text(encoding="utf-8"), md_p.read_text(encoding="utf-8")
    if pair.md_slice is None:
        return patch_tex(orig_tex, raw_md, spec, filename=tex_p.name)
    if (parts := _split_slice(raw_md, pair.md_slice)) is None:
        return PatchResult(False, orig_tex, "", [f"{md_p.name}:L1 缺少切片边界 {pair.md_slice[0]}..{pair.md_slice[1]}，需人工处理"])
    head, lead, core, trail, tail = parts
    frame_errs: list[str] = []
    if pair.expected_md_frame is not None:
        if isinstance(pair.expected_md_frame, tuple):
            exp_head, exp_tail = pair.expected_md_frame
        else:
            ref_txt = pair.expected_md_frame.read_text(encoding="utf-8") if isinstance(pair.expected_md_frame, Path) else pair.expected_md_frame
            rp = _split_slice(ref_txt, pair.md_slice)
            exp_head, exp_tail = (rp[0], rp[4]) if rp else ("", "")
        if head.rstrip("\n") != exp_head.rstrip("\n"):
            frame_errs.append(f"{md_p.name}:L{_diff_line(head, exp_head, 1)} main.md 头部（frontmatter/header）已改动，需人工处理")
        if tail.lstrip("\n") != exp_tail.lstrip("\n"):
            t_ln = raw_md[: len(head) + len(lead) + len(core) + len(trail)].count("\n") + 1
            frame_errs.append(f"{md_p.name}:L{_diff_line(tail, exp_tail, t_ln)} main.md 结构尾部（TOC/include 列表）已改动，需人工处理")
    res = patch_tex(orig_tex, core + ("\n" if orig_tex.endswith("\n") else ""), spec, filename=tex_p.name)
    if frame_errs:
        res.manual_items = frame_errs + res.manual_items
        res.ok = False
    return res


def _atomic_write(path: Path, content: str) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def run_export_cli(pairs: Sequence[SyncPair | tuple[Path | str, Path | str]], spec: SyncSpec = KALMAN_SPEC, argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="将受控学术 Markdown 最小差异回写至 TeX 源文件。")
    ap.add_argument("--apply", action="store_true", help="全部文件校验通过后原子写盘（默认仅预览 diff）。")
    args = ap.parse_args(list(argv) if argv is not None else None)
    norm = [p if isinstance(p, SyncPair) else SyncPair(p[0], p[1]) for p in pairs]
    results = [(p, check_pair_export(p, spec)) for p in norm]
    for _, res in results:
        if res.diff_text:
            sys.stdout.write(res.diff_text)
    if any(not res.ok for _, res in results):
        for _, res in results:
            for item in res.manual_items:
                print(f"[需人工处理] {item}", file=sys.stderr)
            if res.roundtrip_mismatch and not res.manual_items:
                print(f"[校验失败] {res.roundtrip_mismatch}", file=sys.stderr)
        return 1
    if args.apply:
        for p, res in results:
            tp = Path(p.tex_path)
            if tp.read_text(encoding="utf-8") != res.patched_tex:
                _atomic_write(tp, res.patched_tex)
    return 0


def run_import_cli(pairs: Sequence[SyncPair | tuple[Path | str, Path | str]], spec: SyncSpec = KALMAN_SPEC, argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="将 TeX 源文件确定性导入为受控学术 Markdown。")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--check", action="store_true", help="校验 F(TeX) == Markdown 零差异。")
    grp.add_argument("--apply", action="store_true", help="将导入结果写入 Markdown 文件。")
    args = ap.parse_args(list(argv) if argv is not None else None)
    pending: list[tuple[Path, str, str]] = []
    for raw_p in pairs:
        p = raw_p if isinstance(raw_p, SyncPair) else SyncPair(raw_p[0], raw_p[1])
        tp, mp = Path(p.tex_path), Path(p.md_path)
        conv, cur = tex_to_md(tp.read_text(encoding="utf-8"), spec), (mp.read_text(encoding="utf-8") if mp.exists() else "")
        if p.md_slice is not None:
            if (parts := _split_slice(cur, p.md_slice)) is None:
                print(f"[错误] {mp.name}: 缺少切片边界 {p.md_slice[0]}..{p.md_slice[1]}", file=sys.stderr)
                return 1
            head, lead, _, trail, tail = parts
            new_md = f"{head}{lead or chr(10)*2}{conv.strip(chr(10))}{trail or chr(10)*2}{tail}"
        else:
            new_md = conv
        if new_md != cur:
            sys.stdout.write("".join(difflib.unified_diff(cur.splitlines(keepends=True), new_md.splitlines(keepends=True), fromfile=f"a/{mp.name}", tofile=f"b/{mp.name}")))
        pending.append((mp, cur, new_md))
    if args.check:
        return 1 if any(cur != new for _, cur, new in pending) else 0
    if args.apply:
        for mp, cur, new in pending:
            if cur != new or not mp.exists():
                _atomic_write(mp, new)
    return 0
