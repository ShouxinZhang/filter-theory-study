"""构建期公式预渲染（内容哈希缓存）；Node 侧见 scripts/math_prerender.mjs。"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from .paths import SCRIPTS_DIR

NODE_SCRIPT = SCRIPTS_DIR / "math_prerender.mjs"


MJ_PKG = SCRIPTS_DIR / "node_modules" / "mathjax-full"


FONT_DIR_NAME = "mathjax-fonts"


# 不进入数学扫描的片段（与浏览器内 MathJax 的 skipHtmlTags 一致，另加内联 SVG）
PROTECTED = re.compile(r"<(code|pre|script|style|svg)\b.*?</\1>", re.S)


MATH = re.compile(r"\\\[(.+?)\\\]|\\\((.+?)\\\)", re.S)


# 与浏览器内 MathJax 的输出保持一致：容器 position: relative；字号按正文字体的 x 高度缩放
# （构建期不知道读者实际使用的字体，故由 SCALE_SCRIPT 在首帧前量一次写入 --mjx-scale）。
EXTRA_CSS = 'mjx-container[jax="CHTML"]{position:relative;font-size:var(--mjx-scale,113.1%)}'


SCALE_SCRIPT = (
    '<script>(()=>{const s=document.createElement("span");'
    's.style.cssText="position:absolute;visibility:hidden;height:1ex;width:1em";'
    "document.body.appendChild(s);const r=s.getBoundingClientRect();s.remove();"
    'if(r.width)document.documentElement.style.setProperty("--mjx-scale",(100*r.height/r.width/0.442).toFixed(1)+"%")})()</script>'
)


def available() -> str:
    """可用时返回空串，否则返回原因。"""
    if not shutil.which("node"):
        return "未找到 node"
    if not (MJ_PKG / "package.json").exists():
        return f"未安装 mathjax-full（运行：npm install --prefix {SCRIPTS_DIR}）"
    return ""


def _unescape(s: str) -> str:
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def prerender(body: str, macros: dict[str, object], build_dir: Path, out_dir: Path) -> tuple[str, str, dict[str, int]]:
    """返回 (替换后的正文, 样式表, 统计 {total, hit, miss, errors})。"""
    version = json.loads((MJ_PKG / "package.json").read_text(encoding="utf-8"))["version"]
    font_url = FONT_DIR_NAME
    salt = json.dumps([version, "chtml", font_url, macros], ensure_ascii=False, sort_keys=True).encode()
    cache = build_dir / "mathcache"
    cache.mkdir(parents=True, exist_ok=True)

    def key(tex: str, display: bool) -> str:
        return hashlib.sha256(salt + (b"D" if display else b"I") + tex.encode()).hexdigest()

    # 第一遍：收集全部公式及其缓存状态
    found: dict[str, tuple[str, bool]] = {}
    segments: list[tuple[bool, str]] = []
    pos = 0
    for m in PROTECTED.finditer(body):
        segments.append((True, body[pos:m.start()]))
        segments.append((False, m.group(0)))
        pos = m.end()
    segments.append((True, body[pos:]))
    for scan, text in segments:
        if scan:
            for m in MATH.finditer(text):
                display = m.group(1) is not None
                tex = _unescape(m.group(1) if display else m.group(2)).strip()
                found.setdefault(key(tex, display), (tex, display))

    rendered: dict[str, str] = {}
    missing: list[str] = []
    for k in found:
        f = cache / f"{k}.html"
        if f.exists():
            rendered[k] = f.read_text(encoding="utf-8")
        else:
            missing.append(k)

    css_file = cache / f"css-{hashlib.sha256(salt).hexdigest()}.css"
    need_css = not css_file.exists()
    if missing or need_css:
        job = {"macros": macros, "fontURL": font_url, "css": need_css,
               "items": [{"tex": found[k][0], "display": found[k][1]} for k in missing]}
        r = subprocess.run(["node", str(NODE_SCRIPT)], input=json.dumps(job, ensure_ascii=False),
                           capture_output=True, text=True, cwd=SCRIPTS_DIR)
        if r.returncode != 0:
            raise RuntimeError(f"公式预渲染失败：{r.stderr.strip()[-600:]}")
        res = json.loads(r.stdout)
        for k, html_ in zip(missing, res["html"]):
            (cache / f"{k}.html").write_text(html_, encoding="utf-8")
            rendered[k] = html_
        if need_css:
            css_file.write_text(res["css"], encoding="utf-8")

    def sub(m: re.Match[str]) -> str:
        display = m.group(1) is not None
        tex = _unescape(m.group(1) if display else m.group(2)).strip()
        return rendered[key(tex, display)]

    out = "".join(MATH.sub(sub, text) if scan else text for scan, text in segments)

    fonts_src = MJ_PKG / "es5" / "output" / "chtml" / "fonts" / "woff-v2"
    fonts_dst = out_dir / FONT_DIR_NAME
    fonts_dst.mkdir(parents=True, exist_ok=True)
    for f in fonts_src.glob("*.woff"):
        if not (fonts_dst / f.name).exists():
            shutil.copy2(f, fonts_dst / f.name)

    stats = {"total": len(found), "hit": len(found) - len(missing), "miss": len(missing),
             "errors": sum(1 for k in found if "data-mjx-error" in rendered[k])}
    return out, css_file.read_text(encoding="utf-8") + EXTRA_CSS, stats
