"""MathJax-backed rich text layout for SVG charts.

All mathematical expressions in chart text must be explicitly delimited with
$...$ and are pre-rendered into self-contained vector SVG paths via the
repository's mathjax-full (Node) installation.
"""
from __future__ import annotations

import html
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
MATHJAX_SCRIPT = SCRIPTS_DIR / "mathjax_svg.mjs"

# Explicit inline math delimiter $...$ (non-greedy, no empty $$)
_INLINE_MATH_RE = re.compile(r"\$([^$\n]+?)\$")

# Bare math symbols that indicate forgotten $...$ delimiters
_BARE_MATH_RE = re.compile(
    r"([κσθβλμΔΣΩẋẏ]|[₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹]+|(?<![A-Za-z])[A-Za-z]_[A-Za-z0-9]+)"
)


@dataclass(frozen=True)
class MathSvgGlyph:
    vb: tuple[float, float, float, float]
    w_ex: float
    h_ex: float
    va_ex: float
    inner: str


_MATH_CACHE: dict[str, MathSvgGlyph] = {}


def esc(text: Any) -> str:
    """XML/HTML-escape plain text for safe SVG embedding."""
    return html.escape(str(text), quote=True)


def split_math_runs(text: Any) -> list[tuple[str, str]]:
    """Split text into alternating ('text', s) and ('math', tex) runs."""
    s = str(text)
    runs: list[tuple[str, str]] = []
    pos = 0
    for m in _INLINE_MATH_RE.finditer(s):
        if m.start() > pos:
            runs.append(("text", s[pos : m.start()]))
        runs.append(("math", m.group(1).strip()))
        pos = m.end()
    if pos < len(s):
        runs.append(("text", s[pos:]))
    return runs


def find_bare_math(text: Any) -> list[str]:
    """Return any bare math tokens appearing outside $...$ delimiters."""
    found: list[str] = []
    for kind, seg in split_math_runs(text):
        if kind == "text":
            found.extend(m.group(0) for m in _BARE_MATH_RE.finditer(seg))
    return found


def prefetch_math(texts: list[Any], macros: dict[str, Any] | None = None) -> None:
    """Batch-render all uncached $...$ expressions via Node mathjax-full."""
    missing: list[str] = []
    seen: set[str] = set()
    for t in texts:
        for kind, seg in split_math_runs(t):
            if kind == "math" and seg not in _MATH_CACHE and seg not in seen:
                seen.add(seg)
                missing.append(seg)
    if not missing:
        return

    payload = json.dumps({"items": missing, "macros": macros or {}}, ensure_ascii=False)
    res = subprocess.run(
        ["node", str(MATHJAX_SCRIPT)],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        raise RuntimeError(f"MathJax SVG rendering failed (rc={res.returncode}):\n{res.stderr}")
    data = json.loads(res.stdout)
    for src, item in zip(missing, data["items"]):
        vb = item["vb"]
        _MATH_CACHE[src] = MathSvgGlyph(
            vb=(float(vb[0]), float(vb[1]), float(vb[2]), float(vb[3])),
            w_ex=float(item["w_ex"]),
            h_ex=float(item["h_ex"]),
            va_ex=float(item["va_ex"]),
            inner=str(item["inner"]),
        )


def _get_math_glyph(tex: str) -> MathSvgGlyph:
    if tex not in _MATH_CACHE:
        prefetch_math([f"${tex}$"])
    return _MATH_CACHE[tex]


def _plain_text_width(text: str, font_size: float) -> float:
    """Estimate rendered width of a plain text run (CJK + Latin/digits)."""
    w = 0.0
    for ch in text:
        if ord(ch) > 127:
            if ch in "（），。·：；！？「」【】、—":
                w += font_size * 0.85
            else:
                w += font_size * 1.0
        elif ch == " ":
            w += font_size * 0.28
        elif ch in "ilI.,:;!|()[]":
            w += font_size * 0.34
        elif ch in "mwMW":
            w += font_size * 0.80
        else:
            w += font_size * 0.54
    return w


def measure_rich_width(text: Any, font_size: float = 13.0) -> float:
    """Measure total width in px of a mixed plain-text + $...$ MathJax string."""
    ex_px = font_size * 0.50
    total = 0.0
    runs = split_math_runs(text)
    for idx, (kind, seg) in enumerate(runs):
        if kind == "text":
            total += _plain_text_width(seg, font_size)
        else:
            g = _get_math_glyph(seg)
            # Subtle horizontal breathing room next to CJK characters
            pad_l = 1.5 if idx > 0 and runs[idx - 1][1] and ord(runs[idx - 1][1][-1]) > 127 else 0.0
            pad_r = 1.5 if idx + 1 < len(runs) and runs[idx + 1][1] and ord(runs[idx + 1][1][0]) > 127 else 0.0
            total += pad_l + g.w_ex * ex_px + pad_r
    return total


def render_rich_svg(
    text: Any,
    x: float,
    y: float,
    *,
    text_class: str,
    font_size: float,
    anchor: str = "start",
    transform: str = "",
    muted: bool = False,
) -> str:
    """Render plain text + inline $...$ MathJax vector paths aligned to baseline y."""
    runs = split_math_runs(text)
    has_math = any(k == "math" for k, _ in runs)
    if not has_math:
        t_attr = f' transform="{transform}"' if transform else ""
        a_attr = f' text-anchor="{anchor}"' if anchor != "start" else ""
        if transform:
            return f'<text class="{text_class}"{t_attr}{a_attr}>{esc(text)}</text>'
        return f'<text class="{text_class}" x="{x:.1f}" y="{y:.1f}"{a_attr}>{esc(text)}</text>'

    prefetch_math([text])
    ex_px = font_size * 0.50
    total_w = measure_rich_width(text, font_size)

    if anchor == "middle":
        cur_x = (0.0 if transform else x) - total_w / 2.0
    elif anchor == "end":
        cur_x = (0.0 if transform else x) - total_w
    else:
        cur_x = 0.0 if transform else x
    base_y = 0.0 if transform else y

    parts: list[str] = []
    for idx, (kind, seg) in enumerate(runs):
        if kind == "text":
            if not seg:
                continue
            w = _plain_text_width(seg, font_size)
            parts.append(
                f'<text class="{text_class}" x="{cur_x:.2f}" y="{base_y:.2f}">{esc(seg)}</text>'
            )
            cur_x += w
        else:
            g = _get_math_glyph(seg)
            pad_l = 1.5 if idx > 0 and runs[idx - 1][1] and ord(runs[idx - 1][1][-1]) > 127 else 0.0
            pad_r = 1.5 if idx + 1 < len(runs) and runs[idx + 1][1] and ord(runs[idx + 1][1][0]) > 127 else 0.0
            cur_x += pad_l
            w_px = g.w_ex * ex_px
            h_px = g.h_ex * ex_px
            top_y = base_y - (g.h_ex + g.va_ex) * ex_px
            vb_str = f"{g.vb[0]:g} {g.vb[1]:g} {g.vb[2]:g} {g.vb[3]:g}"
            parts.append(
                f'<svg x="{cur_x:.2f}" y="{top_y:.2f}" width="{w_px:.2f}" height="{h_px:.2f}" '
                f'viewBox="{vb_str}" overflow="visible">{g.inner}</svg>'
            )
            cur_x += w_px + pad_r

    color_cls = "ec-math-muted" if muted else "ec-math-fg"
    t_attr = f' transform="{transform}"' if transform else ""
    return f'<g class="{color_cls}"{t_attr}>{"".join(parts)}</g>'


def text_width_px(text: str, cjk_px: float = 14.5, ascii_px: float = 8.0) -> float:
    """Backward-compatible width estimator (delegates to MathJax-aware measure)."""
    return measure_rich_width(text, font_size=cjk_px)
