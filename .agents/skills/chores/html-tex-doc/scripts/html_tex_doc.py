#!/usr/bin/env python3
r"""无分页 HTML / 受控 Markdown 正文 + TeX standalone 出图/算法 的混合文档构建与实时预览工具。

仅依赖 Python 标准库 + TeX Live / dvisvgm。

子命令：
  init <dir> [--title 标题] [--preset basic|academic-md] [--force]
      从技能内置模板初始化 <dir>/src/ 骨架工程。
  build [dir] [--src DIR] [--build-dir DIR] [--out DIR] [--force]
      解析 src/*.md（或 src/doc.html）分配唯一编号 -> 生成 labels.tex -> xelatex/dvisvgm 编译 SVG
      -> 输出单页静态站点（index.html + style.css + reader.js + 静态图资源）。
  serve [dir] [--src DIR] [--build-dir DIR] [--out DIR] [--port 18767] [--host 127.0.0.1]
      启动本地实时预览与类 VS Code 双栏编辑服务（支持局部 MathJax 热刷新、全文搜索与正反向行级高亮对齐）。
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

TEMPLATE_BASIC = SKILL_ROOT / "references" / "templates" / "src"
TEMPLATE_ACADEMIC = SKILL_ROOT / "references" / "templates" / "academic-md" / "src"
TEMPLATE_SRC = TEMPLATE_BASIC  # 向后兼容旧常量名

FORMATS = {"sec": "第 {n} 节", "eq": "式 ({n})", "fig": "图 {n}", "alg": "算法 {n}", "tbl": "表 {n}"}
OPEN_TAG = re.compile(r"<(h2|h3|div|figure)\b([^>]*)>")
ATTR = re.compile(r'([\w-]+)="([^"]*)"')
REF = re.compile(r"\{@([\w:.-]+)(\|n)?\}")
TEX_DEPS = ["common.tex", "macros.tex", "algcommon.tex", "alg2e.tex"]
STATIC_FIG_EXTS = {".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif"}

ACCENT = "#1f6fb2"  # 与 common.tex 中 \definecolor{accent} 保持一致
NAMED = {"black": "#000000", "white": "#ffffff"}


def attrs(s: str) -> dict[str, str]:
    return dict(ATTR.findall(s))


def _keep_loc(a: dict[str, str], include_tex: bool = False) -> str:
    keys = ["data-file", "data-l", "data-l1", "data-l2"]
    if include_tex:
        keys.append("data-tex")
    parts = [f'{k}="{html.escape(a[k], quote=True)}"' for k in keys if k in a]
    return (" " + " ".join(parts)) if parts else ""


def anchor(key: str) -> str:
    return re.sub(r"[^\w-]", "-", key)


def classify(tag: str, a: dict[str, str]) -> str | None:
    cls = a.get("class", "")
    if tag in ("h2", "h3"):
        return "sec"
    if tag == "div" and cls == "eq":
        return "eq" if "data-label" in a else None
    if tag == "div" and cls == "thm":
        return "thm"
    if tag == "figure" and cls in ("fig", "alg", "tbl"):
        return cls
    return None


def auto_label_sections(doc: str) -> str:
    count = 0

    def fn(m: re.Match[str]) -> str:
        nonlocal count
        if m.group(1) in ("h2", "h3") and "data-label" not in m.group(2):
            count += 1
            return f'<{m.group(1)}{m.group(2)} data-label="sec:auto-{count}">'
        return m.group(0)

    return OPEN_TAG.sub(fn, doc)


def number(doc: str, errors: list[str]) -> dict[str, dict[str, str]]:
    labels: dict[str, dict[str, str]] = {}
    sec = [0, 0]
    counters: dict[str, int] = {}
    for m in OPEN_TAG.finditer(doc):
        tag, a = m.group(1), attrs(m.group(2))
        kind = classify(tag, a)
        if not kind:
            continue
        key = a.get("data-label")
        if not key:
            errors.append(f"缺少 data-label：{m.group(0)}")
            continue
        if kind == "sec":
            if tag == "h2":
                sec = [sec[0] + 1, 0]
                num = str(sec[0])
            else:
                sec[1] += 1
                num = f"{sec[0]}.{sec[1]}"
            text = FORMATS["sec"].format(n=num)
        elif kind == "thm":
            k = a.get("data-kind", "定理")
            counters[k] = counters.get(k, 0) + 1
            num = str(counters[k])
            text = f"{k} {num}"
        else:
            counters[kind] = counters.get(kind, 0) + 1
            num = str(counters[kind])
            text = FORMATS[kind].format(n=num)
        if key in labels:
            errors.append(f"重复标签：{key}")
        labels[key] = {"kind": kind, "num": num, "id": anchor(key), "text": text}
    return labels


def write_labels_tex(labels: dict[str, dict[str, str]], build_dir: Path) -> Path:
    path = build_dir / "labels.tex"
    lines = ["% 由 html_tex_doc.py 生成，勿手改。\\lbl{key}{显示文本}{HTML id}"]
    lines += [f"\\lbl{{{k}}}{{{v['text'].replace(' ', '~')}}}{{{v['id']}}}" for k, v in labels.items()]
    new = "\n".join(lines) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != new:
        path.write_text(new, encoding="utf-8")
    return path


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, errors="replace")
    return r.returncode, r.stdout + r.stderr


def _resolve_asset(src_dir: Path, filename: str) -> Path:
    p = src_dir / filename
    return p if p.exists() else TEMPLATE_BASIC / filename


def compile_tex(rel: str, src_dir: Path, build_dir: Path, force: bool, errors: list[str]) -> str | None:
    src = src_dir / rel
    if not src.exists():
        errors.append(f"找不到 TeX 源：{rel}")
        return None
    name = rel.replace("/", "-").removesuffix(".tex")
    wd = build_dir / "tex" / name
    wd.mkdir(parents=True, exist_ok=True)
    svg = wd / f"{name}.svg"

    deps = [src, build_dir / "labels.tex", Path(__file__)]
    for d in TEX_DEPS:
        p = _resolve_asset(src_dir, d)
        if p.exists():
            deps.append(p)
    if not force and svg.exists() and all(svg.stat().st_mtime >= d.stat().st_mtime for d in deps):
        return svg.read_text(encoding="utf-8")

    env = dict(
        os.environ,
        TEXINPUTS=f"{src_dir.resolve()}//:{build_dir.resolve()}:{TEMPLATE_BASIC.resolve()}//:",
    )
    entry = r"\def\pgfsysdriver{pgfsys-dvisvgm.def}\input{" + str(src.resolve()) + "}"
    code, out = _run(
        [
            "xelatex",
            "-no-pdf",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={wd.resolve()}",
            f"-jobname={name}",
            entry,
        ],
        cwd=src.parent,
        env=env,
    )
    log_file = wd / f"{name}.log"
    log = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else out
    if code != 0:
        tail = "\n".join(l for l in log.splitlines() if l.startswith("!") or l.startswith("l."))[:800]
        errors.append(f"xelatex 失败：{rel}\n{tail or out[-600:]}")
        return None
    for key in re.findall(r"UNDEFINED-REF: (\S+)", log):
        errors.append(f"TeX 侧未定义引用：{key}（{rel}）")

    code, out = _run(
        [
            "dvisvgm",
            "--no-fonts",
            "--exact-bbox",
            "--currentcolor",
            "--linkmark=none",
            "--zoom=1.3",
            "-o",
            str(svg.resolve()),
            str((wd / f"{name}.xdv").resolve()),
        ],
        cwd=wd,
    )
    if code != 0 or not svg.exists():
        errors.append(f"dvisvgm 失败：{rel}\n{out[-800:]}")
        return None
    return svg.read_text(encoding="utf-8")


def _hex(v: str) -> str | None:
    v = NAMED.get(v.lower(), v.lower())
    if re.fullmatch(r"#[0-9a-f]{3}", v):
        v = "#" + "".join(c * 2 for c in v[1:])
    return v if re.fullmatch(r"#[0-9a-f]{6}", v) else None


def theme_colors(svg: str) -> str:
    """将 TeX 输出的固定色值改写为主题 CSS 变量。"""
    def tag_fn(m: re.Match[str]) -> str:
        decls: list[str] = []

        def attr_fn(a: re.Match[str]) -> str:
            prop, val = a.group(1), a.group(3)
            h = _hex(val)
            if not h:
                return a.group(0)
            r, g, b = (int(h[i : i + 2], 16) for i in (1, 3, 5))
            if h == ACCENT:
                decls.append(f"{prop}:var(--accent)")
            elif r == g == b == 255:
                decls.append(f"{prop}:var(--bg)")
            elif r == g == b:
                decls.append(f"{prop}:currentColor;{prop}-opacity:{1 - r / 255:.3f}")
            else:
                return a.group(0)
            return ""

        rest = re.sub(r"""\s(fill|stroke)=(['"])([^'"]+)\2""", attr_fn, m.group(2))
        if not decls:
            return m.group(0)
        if re.search(r"\sstyle=", rest):
            rest = re.sub(
                r"""\sstyle=(['"])(.*?)\1""",
                lambda s: f" style={s[1]}{s[2]};{';'.join(decls)}{s[1]}",
                rest,
            )
        else:
            rest += f" style='{';'.join(decls)}'"
        return f"<{m.group(1)}{rest}{m.group(3)}>"

    return re.sub(r"<([a-zA-Z][\w:-]*)(\s[^<>]*?)?(/?)>", lambda m: tag_fn(m) if m.group(2) else m.group(0), svg)


def inline_svg(svg: str, prefix: str, label: str, titles: dict[str, str]) -> str:
    svg = re.sub(r"<\?xml.*?\?>|<!DOCTYPE.*?>|<!--.*?-->", "", svg, flags=re.S).strip()
    ids = set(re.findall(r"""\bid=['"]([^'"]+)['"]""", svg))
    svg = re.sub(r"""\bid=(['"])([^'"]+)\1""", lambda m: f"id={m[1]}{prefix}-{m[2]}{m[1]}", svg)
    svg = re.sub(
        r"""(href=)(['"])#([^'"]+)\2""",
        lambda m: f"{m[1]}{m[2]}#{prefix + '-' + m[3] if m[3] in ids else m[3]}{m[2]}",
        svg,
    )
    svg = re.sub(r"url\(#([^)]+)\)", lambda m: f"url(#{prefix + '-' + m[1] if m[1] in ids else m[1]})", svg)
    svg = re.sub(
        r"""xlink:title=(['"])([^'"]+)\1""",
        lambda m: f"xlink:title={m[1]}{html.escape(titles.get(m[2], m[2]))}{m[1]}",
        svg,
    )
    svg = theme_colors(svg)
    return svg.replace("<svg ", f'<svg class="texfig" role="img" aria-label="{html.escape(label)}" ', 1)


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


def _build_toc_html(toc: list[tuple[int, str, str, str]]) -> str:
    """将 [(level 1|2|3, id, num, title), ...] 构建为支持整卡折叠与分章折叠的目录 HTML。"""
    nodes: list[dict[str, object]] = []
    stack: list[dict[str, object]] = []
    for lv, id_, num, title in toc:
        node: dict[str, object] = {"lv": lv, "id": id_, "num": num, "title": title, "children": []}
        while stack and int(stack[-1]["lv"]) >= lv:  # type: ignore[arg-type]
            stack.pop()
        if stack:
            stack[-1]["children"].append(node)  # type: ignore[attr-defined]
        else:
            nodes.append(node)
        stack.append(node)

    def emit_list(items: list[dict[str, object]]) -> str:
        out: list[str] = ["<ol>"]
        for n in items:
            ch: list[dict[str, object]] = n["children"]  # type: ignore[assignment]
            lv = n["lv"]
            item = (
                f'<button type="button" class="toc-item" data-target="{n["id"]}">'
                f'<span class="toc-num">{n["num"]}</span><span class="toc-txt">{n["title"]}</span>'
                f"</button>"
            )
            if ch:
                out.append(
                    f'<li class="toc-branch" data-lv="{lv}"><div class="toc-row" data-target-id="{n["id"]}">'
                    f'<button type="button" class="toc-caret" aria-expanded="true" title="折叠或展开子节">▾</button>'
                    f"{item}</div>{emit_list(ch)}</li>"
                )
            else:
                out.append(
                    f'<li class="toc-leaf" data-lv="{lv}"><div class="toc-row" data-target-id="{n["id"]}">'
                    f'<span class="toc-caret-pad"></span>{item}</div></li>'
                )
        out.append("</ol>")
        return "".join(out)

    has_sub = any(lv > 1 for lv, _, _, _ in toc)
    sub_btns = (
        '<div class="toc-actions">'
        '<button type="button" class="toc-sub-btn" data-toc-act="fold-sub" title="仅显示顶层章节">收起子节</button>'
        '<button type="button" class="toc-sub-btn" data-toc-act="expand-all" title="展开全部层级">展开全部</button>'
        "</div>"
        if has_sub
        else ""
    )
    return (
        '<nav class="toc" id="doc-toc">'
        '<div class="toc-head">'
        '<button type="button" class="toc-toggle" aria-expanded="true" title="点击折叠或展开目录卡片">'
        '<span class="toc-toggle-icon">▾</span>'
        "<strong>目录</strong>"
        f'<span class="toc-meta">共 {len(toc)} 节</span>'
        "</button>"
        f"{sub_btns}"
        "</div>"
        f'<div class="toc-body">{emit_list(nodes)}</div>'
        "</nav>"
    )


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
        a, body = attrs(m.group(1)), m.group(2)
        if "data-label" not in a:
            return m.group(0)
        L = labels[a["data-label"]]
        i = body.rfind(r"\]")
        if i == -1:
            errors.append(f"{a['data-label']} 公式块未找到 \\] 结尾")
            return m.group(0)
        body = body[:i] + f"\\tag{{{L['num']}}} " + body[i:]
        loc = _keep_loc(a)
        return f'<div class="eq" id="{L["id"]}"{loc}>{body}</div>'

    doc = re.sub(r'<div class="eq"([^>]*)>(.*?)</div>', eq_fn, doc, flags=re.S)

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
    md_files = sorted(src_dir.glob("*.md"))
    doc_path = src_dir / "doc.html"

    errors: list[str] = []
    if md_files:
        from md_conv import compile_markdown_dir

        raw, md_errs = compile_markdown_dir(src_dir)
        errors.extend(md_errs)
    elif doc_path.exists():
        raw = doc_path.read_text(encoding="utf-8")
    else:
        return 1, f"在 {src_dir} 中既未找到 *.md 也未找到 doc.html", ""

    if errors:
        return 1, "Markdown 错误：\n- " + "\n- ".join(errors), ""

    build_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    title_m = re.search(r"<!--\s*title:\s*(.*?)\s*-->", raw)
    title = title_m.group(1) if title_m else "文档"
    doc = re.sub(r"<!--(?!TEX-->|TOC-->).*?-->", "", raw, flags=re.S)

    doc = auto_label_sections(doc)
    labels = number(doc, errors)
    write_labels_tex(labels, build_dir)
    body, n_svg = render(doc, labels, src_dir, build_dir, force, errors)
    if errors:
        return 1, "构建失败：\n- " + "\n- ".join(errors), ""

    macros_file = _resolve_asset(src_dir, "macros.tex")
    config = {
        "tex": {
            "inlineMath": [["\\(", "\\)"]],
            "displayMath": [["\\[", "\\]"]],
            "macros": parse_macros(macros_file),
            "tags": "none",
        }
    }
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
<script>window.MathJax = {json.dumps(config, ensure_ascii=False)};</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
</head>
<body>
<main id="doc-root" class="doc-pane">
{body}
</main>
</body>
</html>
"""
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    (build_dir / "body.html").write_text(body, encoding="utf-8")
    shutil.copy(_resolve_asset(src_dir, "style.css"), out_dir / "style.css")
    shutil.copy(_resolve_asset(src_dir, "reader.js"), out_dir / "reader.js")
    _sync_static_figs(src_dir, out_dir)

    kinds: dict[str, int] = {}
    for v in labels.values():
        kinds[v["kind"]] = kinds.get(v["kind"], 0) + 1
    summary = f"OK  {out_dir / 'index.html'}\n    标签 {len(labels)} 个 {kinds}；内联 SVG {n_svg} 个"
    return 0, summary, body


def cmd_init(args: argparse.Namespace) -> int:
    preset = getattr(args, "preset", "basic") or "basic"
    tpl = TEMPLATE_ACADEMIC if preset == "academic-md" else TEMPLATE_BASIC
    if not tpl.exists():
        print(f"找不到预设模板目录：{tpl}", file=sys.stderr)
        return 1
    dest = Path(args.dir).resolve() / "src"
    if dest.exists() and any(dest.iterdir()) and not args.force:
        print(f"目标已存在且非空：{dest}（如需覆盖请加 --force）", file=sys.stderr)
        return 1
    if dest.exists() and args.force:
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(tpl, dest)
    if not (dest / "common.tex").exists() and (TEMPLATE_BASIC / "common.tex").exists():
        shutil.copy(TEMPLATE_BASIC / "common.tex", dest / "common.tex")
    if args.title:
        for candidate in (dest / "doc.html", dest / "00_摘要.md", dest / "01_正文.md"):
            if candidate.exists():
                txt = candidate.read_text(encoding="utf-8")
                txt = txt.replace("<!-- title: 文档标题 -->", f"<!-- title: {args.title} -->", 1)
                txt = txt.replace("<h1>文档标题</h1>", f"<h1>{html.escape(args.title)}</h1>", 1)
                candidate.write_text(txt, encoding="utf-8")
    print(f"已初始化混合文档骨架（preset={preset}）：{dest}")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    base = Path(args.dir).resolve()
    src_dir = Path(args.src).resolve() if getattr(args, "src", None) else base / "src"
    build_dir = Path(args.build_dir).resolve() if getattr(args, "build_dir", None) else base / "build"
    out_dir = Path(args.out).resolve() if getattr(args, "out", None) else base / "outputs" / "site"
    rc, msg, _ = build_project(src_dir, build_dir, out_dir, force=bool(getattr(args, "force", False)))
    print(msg, file=sys.stderr if rc else sys.stdout)
    return rc


def cmd_serve(args: argparse.Namespace) -> int:
    from dev_server import run_server

    base = Path(args.dir).resolve()
    src_dir = Path(args.src).resolve() if getattr(args, "src", None) else base / "src"
    build_dir = Path(args.build_dir).resolve() if getattr(args, "build_dir", None) else base / "build"
    out_dir = Path(args.out).resolve() if getattr(args, "out", None) else base / "outputs" / "site"
    return run_server(
        src_dir=src_dir,
        build_dir=build_dir,
        out_dir=out_dir,
        host=args.host,
        port=args.port,
        force_first=bool(getattr(args, "force", False)),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="无分页 HTML / Markdown 正文 + TeX 出图混合文档构建与实时编辑工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="在指定目录下生成 src/ 空白工程骨架")
    p_init.add_argument("dir", help="目标工程根目录")
    p_init.add_argument("-t", "--title", help="初始文档标题")
    p_init.add_argument("--preset", choices=["basic", "academic-md"], default="basic", help="骨架模板预设（默认 basic）")
    p_init.add_argument("-f", "--force", action="store_true", help="覆盖已存在的 src/ 目录")
    p_init.set_defaults(func=cmd_init)

    p_build = sub.add_parser("build", help="构建混合文档为单页静态站点")
    p_build.add_argument("dir", nargs="?", default=".", help="工程根目录（默认当前目录）")
    p_build.add_argument("--src", help="显式指定源码目录（默认 <dir>/src）")
    p_build.add_argument("--build-dir", help="显式指定 TeX 中间构建目录（默认 <dir>/build）")
    p_build.add_argument("--out", help="显式指定站点输出目录（默认 <dir>/outputs/site）")
    p_build.add_argument("-f", "--force", action="store_true", help="忽略缓存，强制重编全部 TeX 图/算法")
    p_build.set_defaults(func=cmd_build)

    p_serve = sub.add_parser("serve", help="启动本地实时预览与 Web 双栏编辑服务器")
    p_serve.add_argument("dir", nargs="?", default=".", help="工程根目录（默认当前目录）")
    p_serve.add_argument("--src", help="显式指定源码目录（默认 <dir>/src）")
    p_serve.add_argument("--build-dir", help="显式指定 TeX 中间构建目录（默认 <dir>/build）")
    p_serve.add_argument("--out", help="显式指定站点输出目录（默认 <dir>/outputs/site）")
    p_serve.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    p_serve.add_argument("--port", type=int, default=18767, help="监听端口（默认 18767）")
    p_serve.add_argument("-f", "--force", action="store_true", help="首次构建时强制重编全部 TeX 图/算法")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
