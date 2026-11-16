"""内联 SVG 的主题改色与 id 隔离。"""
from __future__ import annotations

import html
import re

ACCENT = "#1f6fb2"  # 与 common.tex 中 \definecolor{accent} 保持一致


NAMED = {"black": "#000000", "white": "#ffffff"}


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
