"""一次完整构建：源 → 正文 → 页面与静态资源。"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
from pathlib import Path

from .assets import write_site_assets
from .mdconv import compile_markdown_dir
from .numbering import auto_label_sections, number, write_labels_tex
from .paths import _resolve_asset
from .render import parse_macros, render
from .workspace import read_paper_meta, resolve_in_src

STATIC_FIG_EXTS = {".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _sync_static_figs(src_dir: Path, out_dir: Path) -> None:
    figs_src = src_dir / "figs"
    if not figs_src.is_dir():
        return
    figs_dst = out_dir / "figs"
    for f in figs_src.iterdir():
        if f.is_file() and f.suffix.lower() in STATIC_FIG_EXTS:
            figs_dst.mkdir(parents=True, exist_ok=True)
            dst = figs_dst / f.name
            if not dst.exists() or dst.stat().st_mtime_ns < f.stat().st_mtime_ns:
                shutil.copy2(f, dst)


def build_project(
    src_dir: Path,
    build_dir: Path,
    out_dir: Path,
    force: bool = False,
) -> tuple[int, str, str]:
    """执行完整构建：返回 (退出码, 日志/错误文本, 渲染后的 #doc-root 内部 HTML)。"""
    for tool in ("xelatex", "dvisvgm"):
        if not shutil.which(tool):
            return 2, f"缺少依赖工具：{tool}（需安装 TeX Live / dvisvgm）", ""

    src_dir, build_dir, out_dir = src_dir.resolve(), build_dir.resolve(), out_dir.resolve()
    meta = read_paper_meta(src_dir)
    doc_path = src_dir / "doc.html"

    errors: list[str] = []
    if meta.entry in ("main.md", "*.md"):
        raw, md_errs = compile_markdown_dir(src_dir)
        errors.extend(md_errs)
    elif meta.entry == "doc.html":
        raw = doc_path.read_text(encoding="utf-8")
    else:
        return 1, f"在 {src_dir} 中既未找到 *.md 也未找到 doc.html", ""

    if errors:
        return 1, "Markdown 错误：\n- " + "\n- ".join(errors), ""

    build_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    if src_dir.parent == build_dir.parent and not (gi := src_dir.parent / ".gitignore").exists():
        gi.write_text("/build/\n/outputs/\n__pycache__/\n", encoding="utf-8")

    title_m = re.search(r"<!--\s*title:\s*(.*?)\s*-->", raw)
    title = meta.title or (title_m.group(1) if title_m else "文档")
    doc = re.sub(r"<!--(?!TEX-->|TOC-->).*?-->", "", raw, flags=re.S)

    lang = meta.lang or "zh"
    doc = auto_label_sections(doc)
    labels = number(doc, errors, lang=lang)
    write_labels_tex(labels, build_dir)
    body, n_svg = render(doc, labels, src_dir, build_dir, force, errors, lang=lang)
    if errors:
        return 1, "构建失败：\n- " + "\n- ".join(errors), ""

    macros_rel = meta.macros or "macros.tex"
    if resolve_in_src(src_dir, macros_rel) is None:
        return 1, f"构建失败：\n- macros 路径越界：{macros_rel}", ""
    macros_file = _resolve_asset(src_dir, macros_rel)
    macros = parse_macros(macros_file)

    # 公式：优先构建期预渲染（带内容哈希缓存，浏览器端零排版）；不可用时回退到浏览器内 MathJax。
    # HTD_MATH = auto（默认）| browser（强制回退）| prerender（不可用即报错）
    from . import mathpre as math_prerender

    math_mode = os.environ.get("HTD_MATH", "auto")
    math_css, math_note = None, ""
    if math_mode != "browser":
        why = math_prerender.available()
        if why and math_mode == "prerender":
            return 1, f"公式预渲染不可用：{why}", ""
        if why:
            math_note = f"\n    公式：浏览器内排版（{why}）"
        else:
            try:
                body, math_css, st = math_prerender.prerender(body, macros, build_dir, out_dir)
            except RuntimeError as e:
                return 1, str(e), ""
            math_note = f"\n    公式：预渲染 {st['total']} 处不同公式，缓存命中 {st['hit']}，新排版 {st['miss']}"
            if st["errors"]:
                math_note += f"，其中 {st['errors']} 处 TeX 报错（页面内以红字标出）"

    if math_css is not None:
        math_head = f'<style id="mjx-prerendered">{math_css}</style>'
        math_boot = math_prerender.SCALE_SCRIPT + "\n"
    else:
        math_head = None
        math_boot = ""
    config = {
        "tex": {
            "inlineMath": [["\\(", "\\)"]],
            "displayMath": [["\\[", "\\]"]],
            "macros": macros,
            "tags": "none",
        }
    }
    mathjax_browser = (
        f"<script>window.MathJax = {json.dumps(config, ensure_ascii=False)};</script>\n"
        '<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>'
    )
    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="style.css">
<script>/* 首帧前恢复主题与栏宽，避免闪烁 */
try {{ const t = localStorage.getItem("reader.theme"), m = localStorage.getItem("reader.measure");
  if (t === "light" || t === "dark") document.documentElement.setAttribute("data-theme", t);
  if (m) document.documentElement.style.setProperty("--measure", m + "px"); }} catch (e) {{}}</script>
<script defer src="reader.js"></script>
{math_head or mathjax_browser}
</head>
<body>
{math_boot}<main id="doc-root" class="doc-pane">
{body}
</main>
</body>
</html>
"""
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    (build_dir / "body.html").write_text(body, encoding="utf-8")
    write_site_assets(src_dir, out_dir)
    _sync_static_figs(src_dir, out_dir)

    kinds: dict[str, int] = {}
    for v in labels.values():
        kinds[v["kind"]] = kinds.get(v["kind"], 0) + 1
    summary = f"OK  {out_dir / 'index.html'}\n    标签 {len(labels)} 个 {kinds}；内联 SVG {n_svg} 个{math_note}"
    return 0, summary, body
