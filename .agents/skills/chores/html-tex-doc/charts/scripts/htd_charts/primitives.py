"""Pure SVG geometry primitives (paths, bands, areas, glyph instances)."""
from __future__ import annotations

from .scales import LinearScale


def build_polyline(
    xs: list[float],
    ys: list[float],
    x_scale: LinearScale,
    y_scale: LinearScale,
) -> str:
    """Build an SVG path 'd' attribute for an open polyline."""
    pts = [f"{x_scale.map(x):.2f},{y_scale.map(y):.2f}" for x, y in zip(xs, ys)]
    return "M" + "L".join(pts)


def build_band_path(
    xs: list[float],
    lo: list[float],
    hi: list[float],
    x_scale: LinearScale,
    y_scale: LinearScale,
) -> str:
    """Build a closed SVG polygon path between lower and upper bounds."""
    top_pts = [f"{x_scale.map(x):.2f},{y_scale.map(y):.2f}" for x, y in zip(xs, hi)]
    bot_pts = [
        f"{x_scale.map(x):.2f},{y_scale.map(y):.2f}"
        for x, y in zip(reversed(xs), reversed(lo))
    ]
    return "M" + "L".join(top_pts) + "L" + "L".join(bot_pts) + "Z"


def build_area_path(
    xs: list[float],
    ys: list[float],
    baseline: float,
    x_scale: LinearScale,
    y_scale: LinearScale,
) -> str:
    """Build a closed SVG area path from curve (xs, ys) down to y = baseline."""
    pts = [f"{x_scale.map(xs[0]):.2f},{y_scale.map(baseline):.2f}"]
    pts.extend(f"{x_scale.map(x):.2f},{y_scale.map(y):.2f}" for x, y in zip(xs, ys))
    pts.append(f"{x_scale.map(xs[-1]):.2f},{y_scale.map(baseline):.2f}")
    return "M" + "L".join(pts) + "Z"


def use_glyph(
    symbol_id: str,
    cx: float,
    cy: float,
    size: float,
    *,
    color: str | None = None,
    fill_var: str | None = None,
) -> str:
    """Instantiate a registered SVG <symbol> centered at (cx, cy)."""
    half = size / 2.0
    style_parts: list[str] = []
    if color:
        style_parts.append(f"color:{color}")
    if fill_var:
        style_parts.append(f"--ec-glyph-fill:{fill_var}")
    style_attr = f' style="{";".join(style_parts)}"' if style_parts else ""
    return (
        f'<use href="#{symbol_id}" x="{cx - half:.2f}" y="{cy - half:.2f}" '
        f'width="{size:.2f}" height="{size:.2f}"{style_attr}/>'
    )
