"""texsync.json 清单模型、TeX 工程自动发现与一键导入/导出执行器。"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import difflib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from ..paths import TEMPLATE_ACADEMIC
from .codec import parse_tex_units
from .diffpatch import PatchResult, _FLOAT_KINDS, _atomic_write, _split_slice, patch_tex, patch_tex_hierarchy, resolve_tex_input
from .floats import cmd_arg, extract_alg_standalone, tex_algorithm_to_md
from .inline import BOOK_SPEC, EN_SPEC, KALMAN_SPEC, SyncSpec, grab_braced, strip_tex_comment, tex_inline_to_md

MANIFEST_NAME = "texsync.json"
_SKIP_MACROS = frozenset({"htdtitle", "htdsubtitle", "htdfig", "htdfntext", "lbl", "hlink", "cref"})


@dataclass
class TexSyncManifest:
    version: int = 1
    tex_root: str = ".."
    main_tex: str = "main.tex"
    spec: SyncSpec = KALMAN_SPEC
    pairs: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.spec, Mapping):
            self.spec = SyncSpec.from_dict(self.spec)

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "tex_root": self.tex_root, "main_tex": self.main_tex, "spec": self.spec.to_dict(), "pairs": [dict(p) for p in self.pairs]}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> TexSyncManifest:
        return cls(int(d.get("version", 1)), str(d.get("tex_root", "..")), str(d.get("main_tex", "main.tex")), SyncSpec.from_dict(d["spec"]) if "spec" in d else KALMAN_SPEC, [dict(p) for p in d.get("pairs", [])])

    def save(self, manifest_path: Path) -> None:
        _atomic_write(Path(manifest_path), json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n")

    @classmethod
    def load(cls, manifest_path: Path) -> TexSyncManifest:
        return cls.from_dict(json.loads(Path(manifest_path).read_text(encoding="utf-8")))


def _strip_all_comments(tex: str) -> str:
    return "\n".join(strip_tex_comment(ln) for ln in tex.splitlines() if not re.match(r"^\s*%", ln))


def _collect_preamble(main_tex: Path, tex_root: Path) -> str:
    pre = _strip_all_comments(main_tex.read_text(encoding="utf-8")).split(r"\begin{document}", 1)[0]
    subs = [_strip_all_comments(sp.read_text(encoding="utf-8")) for m in re.finditer(r"\\input\{([^}]+)\}", pre) if not m.group(1).strip().startswith("html/") and (sp := resolve_tex_input(m.group(1).strip(), main_tex.parent, tex_root))]
    return "\n".join([pre, *subs])


def _extract_titles(main_tex: Path, spec: SyncSpec) -> tuple[str, str]:
    if not main_tex.is_file():
        return "", ""
    src = _strip_all_comments(main_tex.read_text(encoding="utf-8"))
    mt, ms = re.search(r"\\newcommand\{\\htdtitle\}", src), re.search(r"\\newcommand\{\\htdsubtitle\}", src)
    rt = grab_braced(src, mt.end())[0] if mt and grab_braced(src, mt.end()) else cmd_arg(src, r"\title")
    rs = grab_braced(src, ms.end())[0] if ms and grab_braced(src, ms.end()) else cmd_arg(src, r"\author")
    rt = bt[0] if (rt.startswith(r"\textbf{") and (bt := grab_braced(rt, 7)) and bt[1] == len(rt)) else rt
    rs = re.sub(r"^\\(?:normalsize|large|small)\s+", "", rs.strip())
    return (tex_inline_to_md(rt, spec) if rt and r"\htdtitle" not in rt else ""), (tex_inline_to_md(rs, spec) if rs and r"\htdsubtitle" not in rs else "")


def _inc_names(pairs: Sequence[Mapping[str, Any]]) -> list[str]:
    return [Path(p["md"]).relative_to("src").as_posix() if Path(p["md"]).parts[:1] == ("src",) else Path(p["md"]).name for p in pairs if not p.get("md_slice") and p.get("md") != "src/main.md"]


def _build_main_md_skeleton(main_tex: Path, pairs: Sequence[Mapping[str, Any]], spec: SyncSpec) -> str:
    h1, sub = _extract_titles(main_tex, spec)
    h1 = h1 or main_tex.parent.name
    plain_t, sub_ln, incs = re.sub(r"\[\^[\w-]+\]", "", h1).strip(), (f'\n<p class="subtitle">{sub}</p>' if sub else ""), _inc_names(pairs)
    head = f'---\ntitle: {plain_t}\nmacros: macros.tex\nbib: refs.bib\nbib_order: file\n---\n\n<header class="title">\n<h1>{h1}</h1>{sub_ln}\n</header>'
    return f"{head}\n\n<!--TOC-->\n\n" + "\n".join(f"<!--include {inc}-->" for inc in incs) + ("\n" if incs else "")


def _check_main_md_guard(raw_md: str, sl: tuple[str, str], main_tex: Path, pairs: Sequence[Mapping[str, Any]], spec: SyncSpec, md_name: str) -> list[str]:
    if (parts := _split_slice(raw_md, sl)) is None or not main_tex.is_file():
        return []
    head, lead, core, trail, tail = parts
    errs, (exp_h1, exp_sub) = [], _extract_titles(main_tex, spec)
    fm_m = re.match(r'^---\n(.*?)\n---\s*<header\s+class="title">\s*<h1>(.*?)</h1>\s*(?:<p\s+class="subtitle">(.*?)</p>\s*)?</header>\s*$', head, re.S)
    if not fm_m or (exp_h1 and fm_m.group(2) != exp_h1) or (exp_sub and (fm_m.group(3) or "") != exp_sub):
        errs.append(f"{md_name}:L1 main.md 头部（frontmatter/header）已改动，需人工处理")
    act_incs, rem_tail = re.findall(r"<!--\s*include\s+([^\s]+?)\s*-->", tail), re.sub(r"<!--TOC-->|<!--\s*include\s+[^\s]+?\s*-->", "", tail).strip()
    if not tail.lstrip().startswith("<!--TOC-->") or act_incs != _inc_names(pairs) or rem_tail:
        errs.append(f"{md_name}:L{raw_md[: len(head) + len(lead) + len(core) + len(trail)].count(chr(10)) + 1} main.md 结构尾部（TOC/include 列表）已改动，需人工处理")
    return errs


def _extract_macros_tex(preamble: str) -> str:
    lines, seen = ["% 共享数学宏：TeX 侧与 MathJax 预渲染共用。", "% 约束：仅 \\newcommand{\\name}[n]{body} 形式。"], set()
    if re.search(r"\\usepackage(?:\[[^\]]*\])?\{[^}]*\bbm\b", preamble):
        lines.append(r"\newcommand{\bm}[1]{\boldsymbol{#1}}"); seen.add("bm")
    for m in re.finditer(r"\\newcommand\*?\{\\(\w+)\}(?:\[(\d)\])?\s*\{", preamble):
        name, nargs = m.group(1), m.group(2)
        if name not in seen and name not in _SKIP_MACROS and (br := grab_braced(preamble, m.end() - 1)):
            body = br[0].strip()
            if not any(bad in body for bad in (r"\ding", r"\hyperlink", r"\hypertarget", r"\par", r"\vspace", "@")):
                lines.append(rf"\newcommand{{\{name}}}" + (f"[{nargs}]" if nargs else "") + f"{{{body}}}"); seen.add(name)
    for m in re.finditer(r"\\DeclareMathOperator(\*?)\{\\(\w+)\}\{([^}]+)\}", preamble):
        if m.group(2) not in seen:
            lines.append(rf"\newcommand{{\{m.group(2)}}}{{\operatorname{m.group(1)}{{{m.group(3).strip()}}}}}"); seen.add(m.group(2))
    return "\n".join(lines) + "\n"


def _collect_bib_content(tex_files: Sequence[Path], tex_root: Path, dst_bib: Path) -> str | None:
    keys = [x.strip() for tf in tex_files if tf.is_file() for m in re.finditer(r"\\bibliography\{([^}]+)\}", _strip_all_comments(tf.read_text(encoding="utf-8"))) for x in m.group(1).split(",") if x.strip()]
    chunks, seen_p = [], set()
    for bk in keys:
        bp = (tex_root / (bk if bk.endswith(".bib") else f"{bk}.bib")).resolve()
        if bp.is_file() and bp != dst_bib.resolve() and bp not in seen_p:
            seen_p.add(bp); chunks.append(bp.read_text(encoding="utf-8").strip())
    return ("\n\n".join(c for c in chunks if c) + "\n") if chunks else None


def render_tex_hierarchy(tex_path: Path, tex_root: Path, spec: SyncSpec, algs_out: dict[str, str] | None = None, alg_ctr: list[int] | None = None, _seen: frozenset[Path] = frozenset()) -> str:
    ctr, raw_tex = (alg_ctr if alg_ctr is not None else [0]), tex_path.read_text(encoding="utf-8")
    units, nxt_seen = parse_tex_units(raw_tex, spec), _seen | {tex_path.resolve()}
    for u in units:
        if u.kind == "algorithm":
            ctr[0] += 1; u.md_text = tex_algorithm_to_md(u.tex_text, spec, ctr[0])[0]
            if algs_out is not None:
                algs_out.__setitem__(*extract_alg_standalone(u.tex_text, spec, ctr[0]))
        elif u.kind == "tex_input" and (sp := resolve_tex_input(u.meta, tex_path.parent, tex_root)) and sp.resolve() not in nxt_seen:
            sub_u = parse_tex_units(sp.read_text(encoding="utf-8"), spec)
            if len(sub_u) == 1 and sub_u[0].kind in _FLOAT_KINDS:
                su = sub_u[0]
                if su.kind == "algorithm":
                    ctr[0] += 1; su.md_text = tex_algorithm_to_md(su.tex_text, spec, ctr[0])[0]
                    if algs_out is not None:
                        algs_out.__setitem__(*extract_alg_standalone(su.tex_text, spec, ctr[0]))
                u.md_text = su.md_text
            else:
                sub_rel = sp.resolve().relative_to(tex_root.resolve()).as_posix()
                u.md_text = f"<!--tex-file: {sub_rel}-->\n\n{render_tex_hierarchy(sp, tex_root, spec, algs_out, ctr, nxt_seen).strip(chr(10))}\n\n<!--/tex-file-->"
    return ("".join(u.md_text + u.trailing_sep for u in units) + ("\n" if raw_tex.endswith("\n") else "")) if raw_tex else ""


def discover_tex_project(tex_root: Path, html_dir: Path) -> TexSyncManifest:
    tex_root_abs, html_dir_abs = Path(tex_root).resolve(), Path(html_dir).resolve()
    if (mp := html_dir_abs / MANIFEST_NAME).is_file():
        return TexSyncManifest.load(mp)
    if not (main_tex := tex_root_abs / "main.tex").is_file():
        raise FileNotFoundError(f"未找到 TeX 主文件: {main_tex}")
    clean_main = _strip_all_comments(main_tex.read_text(encoding="utf-8"))
    cm = re.search(r"\\documentclass(?:\[[^\]]*\])?\{([^}]+)\}", clean_main)
    dcls = cm.group(1).strip().lower() if cm else ""
    base_spec = BOOK_SPEC if "book" in dcls else (EN_SPEC if dcls in ("article", "ieeetran", "revtex4-2") else KALMAN_SPEC)
    auto_list, num_names = list(base_spec.auto_envs), {e for e, _ in base_spec.num_envs}
    for m in re.finditer(r"\\newtheorem\*?\{(\w+)\}(?:\[[^\]]*\])?\{([^}]+)\}", _collect_preamble(main_tex, tex_root_abs)):
        en, zh = m.group(1), m.group(2).strip()
        if not en.startswith("htd") and en != base_spec.proof_env[0] and en not in num_names:
            idx = next((k for k, (e, _) in enumerate(auto_list) if e == en), -1)
            auto_list[idx : idx + 1] = [(en, zh)] if idx >= 0 else [*auto_list[idx : idx + 1]]
            if idx < 0:
                auto_list.append((en, zh))
    doc_body = clean_main.split(r"\begin{document}", 1)[1].split(r"\end{document}", 1)[0] if r"\begin{document}" in clean_main else clean_main
    pairs: list[dict[str, Any]] = []
    if am := re.search(r"\\begin\{c?abstract\}\s*\\input\{([^}]+)\}\s*\\end\{c?abstract\}", doc_body):
        if ap := resolve_tex_input(am.group(1).strip(), tex_root_abs, tex_root_abs):
            pairs.append({"tex": ap.resolve().relative_to(tex_root_abs).as_posix(), "md": "src/main.md", "md_slice": ["</header>", "<!--TOC-->"], "guard_main_tex": "main.tex"})
        doc_body = doc_body[: am.start()] + doc_body[am.end() :]
    scan_body = doc_body.split(r"\mainmatter", 1)[1] if r"\mainmatter" in doc_body else doc_body
    used_mds, chap_files = set(), []
    for idx_c, m in enumerate(re.finditer(r"\\input\{([^}]+)\}", scan_body)):
        if cp := resolve_tex_input(m.group(1).strip(), tex_root_abs, tex_root_abs):
            stem = cp.stem
            md_rel = f"src/{stem}.md" if ((html_dir_abs / "src" / f"{stem}.md").is_file() or (re.match(r"^\d{2}[_-]", stem) and f"src/{stem}.md" not in used_mds)) else f"src/{idx_c:02d}_{stem}.md"
            used_mds.add(md_rel); chap_files.append(cp); pairs.append({"tex": cp.resolve().relative_to(tex_root_abs).as_posix(), "md": md_rel})
    bib_tex = next((bm.group(1) for tf in [*chap_files, main_tex] if (bm := re.search(r"^(\\bibliography\{[^}]+\})\s*$", _strip_all_comments(tf.read_text(encoding="utf-8")), re.M))), base_spec.bib_tex)
    spec = SyncSpec(base_spec.ref_templates, tuple(auto_list), base_spec.num_envs, base_spec.proof_env, bib_tex, base_spec.colspecs, base_spec.heading_cmds)
    return TexSyncManifest(1, os.path.relpath(tex_root_abs, html_dir_abs).replace(os.sep, "/"), "main.tex", spec, pairs)


def execute_import(tex_root: Path, html_dir: Path, *, check: bool = False, apply: bool = False) -> int:
    tex_root_abs, html_dir_abs = Path(tex_root).resolve(), Path(html_dir).resolve()
    manifest_p = html_dir_abs / MANIFEST_NAME
    has_manifest = manifest_p.is_file()
    manifest = TexSyncManifest.load(manifest_p) if has_manifest else discover_tex_project(tex_root_abs, html_dir_abs)
    algs_out, alg_ctr, md_targets, main_tex_p = {}, [0], {}, tex_root_abs / manifest.main_tex
    for pd in manifest.pairs:
        tp, mp = tex_root_abs / pd["tex"], html_dir_abs / pd["md"]
        conv = render_tex_hierarchy(tp, tex_root_abs, manifest.spec, algs_out=algs_out, alg_ctr=alg_ctr)
        base_md = md_targets.get(mp, mp.read_text(encoding="utf-8") if mp.is_file() else "")
        if sl_raw := pd.get("md_slice"):
            sl = (str(sl_raw[0]), str(sl_raw[1]))
            base_md = base_md or (_build_main_md_skeleton(main_tex_p, manifest.pairs, manifest.spec) if mp.name == "main.md" else "")
            if (parts := _split_slice(base_md, sl)) is None:
                print(f"[错误] {mp.name}: 缺少切片边界 {sl[0]}..{sl[1]}", file=sys.stderr); return 1
            md_targets[mp] = f"{parts[0]}{parts[1] or chr(10)*2}{conv.strip(chr(10))}{parts[3] or chr(10)*2}{parts[4]}"
        else:
            md_targets[mp] = conv
    if not (main_mp := html_dir_abs / "src/main.md").is_file() and main_mp not in md_targets:
        md_targets[main_mp] = _build_main_md_skeleton(main_tex_p, manifest.pairs, manifest.spec)
    has_diff = False
    for mp, new_md in md_targets.items():
        cur = mp.read_text(encoding="utf-8") if mp.is_file() else ""
        if cur != new_md:
            has_diff = True; lbl = mp.relative_to(html_dir_abs).as_posix() if mp.is_relative_to(html_dir_abs) else mp.name
            sys.stdout.write("".join(difflib.unified_diff(cur.splitlines(keepends=True), new_md.splitlines(keepends=True), fromfile=f"a/{lbl}", tofile=f"b/{lbl}")))
    if check or not apply:
        return (1 if has_diff else 0) if check else 0
    src_dir = html_dir_abs / "src"; src_dir.mkdir(parents=True, exist_ok=True)
    if not has_manifest:
        if not (src_dir / "macros.tex").exists() and main_tex_p.is_file():
            _atomic_write(src_dir / "macros.tex", _extract_macros_tex(_collect_preamble(main_tex_p, tex_root_abs)))
        if (bib_txt := _collect_bib_content([main_tex_p, *(tex_root_abs / p["tex"] for p in manifest.pairs)], tex_root_abs, src_dir / "refs.bib")) is not None:
            _atomic_write(src_dir / "refs.bib", bib_txt)
        elif not (src_dir / "refs.bib").exists():
            _atomic_write(src_dir / "refs.bib", "")
        if not (gi := html_dir_abs / ".gitignore").exists():
            _atomic_write(gi, "/build/\n/outputs/\n__pycache__/\n")
        manifest.save(manifest_p)
    for alg_rel, alg_doc in algs_out.items():
        if not (ap := src_dir / alg_rel).is_file() or ap.read_text(encoding="utf-8") != alg_doc:
            _atomic_write(ap, alg_doc)
    if any(r"\input{alg2e}" in d for d in algs_out.values()) and not (src_dir / "alg2e.tex").exists() and (tpl_alg := TEMPLATE_ACADEMIC / "alg2e.tex").is_file():
        _atomic_write(src_dir / "alg2e.tex", tpl_alg.read_text(encoding="utf-8"))
    for mp, new_md in md_targets.items():
        if not mp.is_file() or mp.read_text(encoding="utf-8") != new_md:
            _atomic_write(mp, new_md)
    return 0


def execute_export(html_dir: Path, *, tex_root: Path | None = None, apply: bool = False) -> int:
    html_dir_abs = Path(html_dir).resolve()
    if not (manifest_p := html_dir_abs / MANIFEST_NAME).is_file():
        print(f"[错误] 未找到同步清单 {manifest_p}，请先运行 export-tex --init-tex 或 import-tex --apply。", file=sys.stderr); return 1
    manifest = TexSyncManifest.load(manifest_p)
    tex_root_abs = Path(tex_root).resolve() if tex_root is not None else (html_dir_abs / manifest.tex_root).resolve()
    all_res: list[tuple[Path, PatchResult]] = []
    for pd in manifest.pairs:
        tp, mp = tex_root_abs / pd["tex"], html_dir_abs / pd["md"]
        if not tp.is_file() or not mp.is_file():
            all_res.append((tp, PatchResult(False, "", "", [f"缺失同步文件 {pd['tex']} 或 {pd['md']}，需人工处理"]))); continue
        raw_md = mp.read_text(encoding="utf-8")
        if sl_raw := pd.get("md_slice"):
            sl, orig_tex = (str(sl_raw[0]), str(sl_raw[1])), tp.read_text(encoding="utf-8")
            if (parts := _split_slice(raw_md, sl)) is None:
                all_res.append((tp, PatchResult(False, orig_tex, "", [f"{mp.name}:L1 缺少切片边界 {sl[0]}..{sl[1]}，需人工处理"]))); continue
            g_errs = _check_main_md_guard(raw_md, sl, tex_root_abs / str(pd["guard_main_tex"]), manifest.pairs, manifest.spec, mp.name) if pd.get("guard_main_tex") else []
            res = patch_tex(orig_tex, parts[2] + ("\n" if orig_tex.endswith("\n") else ""), manifest.spec, filename=pd["tex"])
            if g_errs:
                res.manual_items = g_errs + res.manual_items; res.ok = False
            all_res.append((tp, res))
        else:
            all_res.extend(patch_tex_hierarchy(tp, raw_md, tex_root_abs, manifest.spec, md_name=pd["md"]))
    for _, res in all_res:
        if res.diff_text:
            sys.stdout.write(res.diff_text)
    if any(not res.ok for _, res in all_res):
        for _, res in all_res:
            for item in res.manual_items:
                print(f"[需人工处理] {item}", file=sys.stderr)
            if res.roundtrip_mismatch and not res.manual_items:
                print(f"[校验失败] {res.roundtrip_mismatch}", file=sys.stderr)
        return 1
    if apply:
        for tp, res in all_res:
            if tp.read_text(encoding="utf-8") != res.patched_tex:
                _atomic_write(tp, res.patched_tex)
    return 0
