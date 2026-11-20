"""从受控学术 Markdown 工程机械生成可编译父级 ctexart 工程与 texsync.json。"""
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from ..paths import SKILL_ROOT
from ..workspace import INCLUDE_RE, parse_frontmatter, read_paper_meta, resolve_in_src
from .codec import md_to_tex
from .inline import EN_SPEC, KALMAN_SPEC, SyncSpec, md_inline_to_tex

TEMPLATE_TEX_ARTICLE = SKILL_ROOT / "references" / "templates" / "tex-article"
_BIB_KEY_RE = re.compile(r"@(?!comment\b|preamble\b|string\b)[A-Za-z]+\s*\{\s*([^,\s}]+)", re.I)
_HEADER_RE = re.compile(r"<header\b[^>]*>(.*?)</header>", re.I | re.S)
_H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
_SUB_RE = re.compile(r'<p\s+class=["\']subtitle["\'][^>]*>(.*?)</p>', re.I | re.S)

_EXTRA_REFS: tuple[tuple[str, str, str], ...] = (
    ("alg:", r"算法~\ref{", ""), ("prop:", r"命题~\ref{", ""), ("lem:", r"引理~\ref{", ""),
    ("def:", r"定义~\ref{", ""), ("ass:", r"假设~\ref{", ""),
)
_EXTRA_ENVS: tuple[tuple[str, str], ...] = (
    ("proposition", "命题"), ("lemma", "引理"), ("definition", "定义"), ("assumption", "假设"), ("remark", "注"),
)


def _atomic_write(path: Path, content: str, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        if mode is not None:
            os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def _spec_to_dict(spec: SyncSpec) -> dict[str, object]:
    if hasattr(spec, "to_dict"):
        return spec.to_dict()  # type: ignore[no-any-return]
    data: dict[str, object] = {
        "ref_templates": [list(x) for x in spec.ref_templates],
        "auto_envs": [list(x) for x in spec.auto_envs],
        "num_envs": [list(x) for x in spec.num_envs],
        "proof_env": list(spec.proof_env),
        "bib_tex": spec.bib_tex,
        "colspecs": [[n, c] for n, c in spec.colspecs],
    }
    if hasattr(spec, "heading_cmds"):
        data["heading_cmds"] = list(getattr(spec, "heading_cmds"))
    return data


def _build_article_spec(md_blobs: list[str], bib_tex: str, *, is_en: bool = False) -> SyncSpec:
    if is_en:
        return replace(EN_SPEC, bib_tex=bib_tex) if bib_tex != EN_SPEC.bib_tex else EN_SPEC
    joined = "\n".join(md_blobs)
    known_pfx = {p for p, _, _ in KALMAN_SPEC.ref_templates}
    add_refs = tuple(r for r in _EXTRA_REFS if r[0] not in known_pfx and f"{{@{r[0]}" in joined)
    known_kinds = {k for _, k in KALMAN_SPEC.auto_envs} | {k for _, k in KALMAN_SPEC.num_envs}
    add_envs = tuple(e for e in _EXTRA_ENVS if e[1] not in known_kinds and re.search(rf"^:::\s+{re.escape(e[1])}\b", joined, re.M))
    spec = KALMAN_SPEC
    if add_refs:
        spec = replace(spec, ref_templates=(*spec.ref_templates, *add_refs))
    if add_envs:
        spec = replace(spec, auto_envs=(*spec.auto_envs, *add_envs))
    return replace(spec, bib_tex=bib_tex) if bib_tex != spec.bib_tex else spec


def _format_bib_setup(bib_path: Path | None) -> str:
    if bib_path is None or not bib_path.is_file():
        return ""
    keys = [m.group(1) for m in _BIB_KEY_RE.finditer(bib_path.read_text(encoding="utf-8"))]
    lines = ["", r"\bibliographystyle{unsrt}"]
    if keys:
        body = ",%\n  ".join(",".join(keys[i : i + 12]) for i in range(0, len(keys), 12))
        lines.append(f"\\AtBeginDocument{{%\n  \\nocite{{{body}}}%\n}}")
    return "\n".join(lines) + "\n"


def scaffold_tex_project(html_dir: Path, tex_root: Path | None = None, *, apply: bool = False, force: bool = False) -> int:
    hdir = Path(html_dir).resolve()
    src_dir = hdir / "src"
    if not src_dir.is_dir():
        print(f"[错误] 未找到源码目录：{src_dir}", file=sys.stderr)
        return 1
    root = Path(tex_root).resolve() if tex_root is not None else (hdir.parent if hdir.name == "html" else hdir / "tex")
    if (root / "main.tex").exists() and not force:
        print(f"[错误] 目标 main.tex 已存在：{root / 'main.tex'}（如需覆盖请加 --force）", file=sys.stderr)
        return 1
    if not TEMPLATE_TEX_ARTICLE.is_dir():
        print(f"[错误] 缺少内置 tex-article 模板目录：{TEMPLATE_TEX_ARTICLE}", file=sys.stderr)
        return 1

    src_rel = Path(os.path.relpath(src_dir, root)).as_posix()
    tex_root_rel = Path(os.path.relpath(root, hdir)).as_posix()
    main_md_path = src_dir / "main.md"
    fm: dict[str, str] = {}
    chapters: list[tuple[str, str, str]] = []
    abs_core = ""

    if main_md_path.is_file():
        main_txt = main_md_path.read_text(encoding="utf-8")
        fm, body, _ = parse_frontmatter(main_txt)
        if hm := _HEADER_RE.search(body):
            m1, ms = _H1_RE.search(hm.group(1)), _SUB_RE.search(hm.group(1))
            h1_md = m1.group(1).strip() if m1 else (fm.get("title") or hdir.name)
            sub_md = ms.group(1).strip() if ms else ""
        else:
            h1_md, sub_md = (fm.get("title") or read_paper_meta(src_dir).title or hdir.name), ""
        i0 = main_txt.find("</header>")
        i1 = main_txt.find("<!--TOC-->", i0 + 9) if i0 != -1 else -1
        abs_core = main_txt[i0 + 9 : i1].strip("\n") if (i0 != -1 and i1 != -1) else ""
        for ln in body.split("\n"):
            if im := INCLUDE_RE.match(ln):
                resolved = resolve_in_src(src_dir, im.group(1))
                if resolved is None or not resolved[0].is_file() or resolved[0] == main_md_path:
                    print(f"[错误] main.md 引用了无效章节：{im.group(1)}", file=sys.stderr)
                    return 1
                inc_p, rel_p = resolved
                sec_stem = rel_p[:-3] if rel_p.endswith(".md") else rel_p
                chapters.append((f"sections/{sec_stem}", f"src/{rel_p}", inc_p.read_text(encoding="utf-8")))
        if not chapters and not abs_core.strip():
            chapters.append(("sections/main", "src/main.md", body.lstrip("\n") if fm else main_txt))
    else:
        md_files = sorted(p for p in src_dir.glob("*.md") if p.is_file())
        if not md_files:
            print(f"[错误] 未找到受控 Markdown 源文件：{src_dir}", file=sys.stderr)
            return 1
        h1_md, sub_md = (read_paper_meta(src_dir).title or hdir.name), ""
        chapters = [(f"sections/{p.stem}", f"src/{p.name}", p.read_text(encoding="utf-8")) for p in md_files]

    is_en = (fm.get("lang") or "").lower().startswith("en")
    bib_name = fm.get("bib") or "refs.bib"
    bib_path = src_dir / bib_name
    has_abs = bool(abs_core.strip())
    spec = _build_article_spec([h1_md, sub_md, abs_core, *(c[2] for c in chapters)], rf"\bibliography{{{src_rel}/{Path(bib_name).stem}}}", is_en=is_en)

    tpl_main = (TEMPLATE_TEX_ARTICLE / "main.tex").read_text(encoding="utf-8")
    tpl_pre = (TEMPLATE_TEX_ARTICLE / "preamble.tex").read_text(encoding="utf-8")
    tpl_sh = (TEMPLATE_TEX_ARTICLE / "build.sh").read_text(encoding="utf-8")
    tpl_gi = (TEMPLATE_TEX_ARTICLE / "gitignore").read_text(encoding="utf-8")
    if is_en:
        tpl_main = tpl_main.replace(r"\documentclass[UTF8,11pt,a4paper]{ctexart}", r"\documentclass[11pt,a4paper]{article}")
        for zh_s, en_s in (("证明", "Proof"), ("定理", "Theorem"), ("推论", "Corollary"), ("命题", "Proposition"), ("引理", "Lemma"), ("定义", "Definition"), ("假设", "Assumption"), ("算例", "Example"), ("评注", "Remark"), ("问题", "Problem"), ("{注}", "{Remark}")):
            tpl_pre = tpl_pre.replace(zh_s, en_s)
    if src_rel != "html/src":
        tpl_pre, tpl_sh = tpl_pre.replace("html/src", src_rel), tpl_sh.replace("html/src", src_rel)

    abs_tex_blk = "\n\\begin{abstract}\n\\input{sections/abstract}\n\\end{abstract}\n" if has_abs else ""
    main_tex = (
        tpl_main.replace("__HTD_TITLE__", md_inline_to_tex(h1_md, spec))
        .replace("__HTD_SUBTITLE__", md_inline_to_tex(sub_md, spec) if sub_md else "")
        .replace("__HTD_BIB_SETUP__", _format_bib_setup(bib_path if bib_path.is_file() else None))
        .replace("__HTD_ABSTRACT__", abs_tex_blk)
        .replace("__HTD_SECTIONS__", "\n\n".join(f"\\input{{{s}}}" for s, _, _ in chapters))
    )

    files: list[tuple[Path, str, int | None]] = [
        (root / "main.tex", main_tex, None), (root / "preamble.tex", tpl_pre, None),
        (root / "build.sh", tpl_sh, 0o755), (root / ".gitignore", tpl_gi, None),
    ]
    pairs_json: list[dict[str, object]] = []
    if has_abs:
        files.append((root / "sections/abstract.tex", md_to_tex(abs_core + "\n", spec), None))
        pairs_json.append({"tex": "sections/abstract.tex", "md": "src/main.md", "md_slice": ["</header>", "<!--TOC-->"], "guard_main_tex": "main.tex"})
    for sec_no_ext, md_rel, md_txt in chapters:
        files.append((root / f"{sec_no_ext}.tex", md_to_tex(md_txt, spec), None))
        pairs_json.append({"tex": f"{sec_no_ext}.tex", "md": md_rel})

    manifest_path = hdir / "texsync.json"
    manifest_obj = {"version": 1, "tex_root": tex_root_rel, "main_tex": "main.tex", "spec": _spec_to_dict(spec), "pairs": pairs_json}
    manifest_txt = json.dumps(manifest_obj, ensure_ascii=False, indent=2) + "\n"
    if not apply:
        for fp, _, _ in [*files, (manifest_path, manifest_txt, None)]:
            print(f"[预览] 将生成 {fp}")
        return 0
    for fp, content, mode in files:
        _atomic_write(fp, content, mode=mode)
    _atomic_write(manifest_path, manifest_txt)
    print(f"已生成父级 LaTeX 工程：{root}（清单：{manifest_path}）")
    return 0
