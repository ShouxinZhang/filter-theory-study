"""High-level Chart builder and SVG canvas assembler.

All visual styling comes from external Theme CSS packs and SVG glyphs;
all inline $...$ mathematics is pre-rendered via MathJax SVG paths;
callouts are clamped to the plot region to prevent header collisions.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable

from .math_text import find_bare_math, measure_rich_width, prefetch_math, render_rich_svg
from .primitives import build_area_path, build_band_path, build_polyline, use_glyph
from .scales import LinearScale, fmt_tick
from .theme import GlyphAsset, Theme

DrawCallback = Callable[
    [LinearScale, LinearScale, float, float, float, float],
    tuple[list[str], list[str]],
]


class Chart:
    """Chainable semantic chart builder emitting theme-aware inline SVGs."""

    def __init__(
        self,
        title: str,
        *,
        subtitle: str = "",
        theme: str | Theme = "editorial-academic",
        override_css: Path | None = None,
        x_domain: tuple[float, float] = (0.0, 1.0),
        y_domain: tuple[float, float] = (0.0, 1.0),
        x_ticks: list[float] | None = None,
        y_ticks: list[float] | None = None,
        x_label: str = "",
        y_label: str = "",
        x_grid: bool = False,
        x_left: float | None = None,
        x_right: float | None = None,
        strict_math: bool = True,
    ) -> None:
        self.title = title
        self.subtitle = subtitle
        self.theme = (
            theme
            if isinstance(theme, Theme)
            else Theme(theme, override_css=override_css)
        )
        self.x_min, self.x_max = float(x_domain[0]), float(x_domain[1])
        self.y_min, self.y_max = float(y_domain[0]), float(y_domain[1])
        self.x_ticks = list(x_ticks or [])
        self.y_ticks = list(y_ticks or [])
        self.x_label = x_label
        self.y_label = y_label
        self.x_grid = x_grid
        self.x_left = float(x_left) if x_left is not None else self.theme.margin_left
        self.x_right = (
            float(x_right)
            if x_right is not None
            else self.theme.width - self.theme.margin_right
        )
        self.strict_math = strict_math

        self._legend_items: list[dict[str, Any]] = []
        self._layers: list[DrawCallback] = []
        self._used_glyphs: dict[str, GlyphAsset] = {}
        self._all_texts: list[str] = [title, subtitle, x_label, y_label]
        self._callout_y_positions: list[tuple[str, float]] = []

    def _register_glyph(self, name: str) -> GlyphAsset:
        asset = self.theme.load_glyph(name)
        self._used_glyphs[asset.name] = asset
        return asset

    def add_legend(
        self,
        label: str,
        *,
        kind: str = "line",
        role: str = "fg",
        dashed: bool = False,
        fill_role: str | None = None,
    ) -> "Chart":
        self._all_texts.append(label)
        self._legend_items.append(
            {
                "label": label,
                "kind": kind,
                "color": self.theme.color(role),
                "dashed": dashed,
                "fill": self.theme.color(fill_role) if fill_role else None,
            }
        )
        return self

    def add_line(
        self,
        xs: list[float],
        ys: list[float],
        *,
        role: str = "primary",
        dashed: bool = False,
        thin: bool = False,
    ) -> "Chart":
        color = self.theme.color(role)
        cls_parts = ["ec-line-thin" if thin else "ec-line"]
        if dashed:
            cls_parts.append("ec-line-dashed")
        cls = " ".join(cls_parts)

        def _draw(x_sc: LinearScale, y_sc: LinearScale, *_args: float):
            d = build_polyline(xs, ys, x_sc, y_sc)
            return [f'<path class="{cls}" stroke="{color}" d="{d}"/>'], []

        self._layers.append(_draw)
        return self

    def add_band(
        self,
        xs: list[float],
        lo: list[float],
        hi: list[float],
        *,
        role: str = "primary",
        opacity: float = 0.20,
        show_edges: bool = True,
    ) -> "Chart":
        color = self.theme.color(role)

        def _draw(x_sc: LinearScale, y_sc: LinearScale, *_args: float):
            parts = [
                f'<path d="{build_band_path(xs, lo, hi, x_sc, y_sc)}" '
                f'fill="{color}" fill-opacity="{opacity:.2f}"/>'
            ]
            if show_edges:
                parts.append(
                    f'<path class="ec-band-edge" stroke="{color}" d="{build_polyline(xs, hi, x_sc, y_sc)}"/>'
                )
                parts.append(
                    f'<path class="ec-band-edge" stroke="{color}" d="{build_polyline(xs, lo, x_sc, y_sc)}"/>'
                )
            return parts, []

        self._layers.append(_draw)
        return self

    def add_area(
        self,
        xs: list[float],
        ys: list[float],
        *,
        baseline: float = 0.0,
        role: str = "primary",
        opacity: float = 0.22,
    ) -> "Chart":
        color = self.theme.color(role)

        def _draw(x_sc: LinearScale, y_sc: LinearScale, *_args: float):
            d = build_area_path(xs, ys, baseline, x_sc, y_sc)
            return [f'<path d="{d}" fill="{color}" fill-opacity="{opacity:.2f}"/>'], []

        self._layers.append(_draw)
        return self

    def add_markers(
        self,
        xs: list[float],
        ys: list[float],
        *,
        glyph: str = "star",
        size: float = 9.0,
        role: str = "fg",
        fill_role: str | None = None,
    ) -> "Chart":
        asset = self._register_glyph(glyph)
        color = self.theme.color(role)
        fill_var = self.theme.color(fill_role) if fill_role else None

        def _draw(x_sc: LinearScale, y_sc: LinearScale, *_args: float):
            parts = [
                use_glyph(
                    asset.symbol_id,
                    x_sc.map(x),
                    y_sc.map(y),
                    size,
                    color=color,
                    fill_var=fill_var,
                )
                for x, y in zip(xs, ys)
            ]
            return parts, []

        self._layers.append(_draw)
        return self

    def add_scatter(
        self,
        xs: list[float],
        ys: list[float],
        *,
        r: float = 2.6,
        role: str = "primary",
        opacity: float = 0.45,
    ) -> "Chart":
        color = self.theme.color(role)

        def _draw(x_sc: LinearScale, y_sc: LinearScale, *_args: float):
            parts = [
                f'<circle cx="{x_sc.map(x):.2f}" cy="{y_sc.map(y):.2f}" r="{r:.1f}" '
                f'fill="{color}" fill-opacity="{opacity:.2f}"/>'
                for x, y in zip(xs, ys)
            ]
            return parts, []

        self._layers.append(_draw)
        return self

    def add_vline(
        self,
        x: float,
        *,
        marker_glyph: str | None = None,
        marker_size: float = 11.0,
        marker_role: str = "fg",
    ) -> "Chart":
        asset = self._register_glyph(marker_glyph) if marker_glyph else None
        color = self.theme.color(marker_role)

        def _draw(x_sc: LinearScale, _y_sc: LinearScale, _xl: float, _xr: float, yt: float, yb: float):
            tx = x_sc.map(x)
            parts = [
                f'<line class="ec-ref-line" x1="{tx:.2f}" x2="{tx:.2f}" y1="{yt:.1f}" y2="{yb:.1f}"/>'
            ]
            if asset:
                parts.append(use_glyph(asset.symbol_id, tx, yb - 7.0, marker_size, color=color))
            return parts, []

        self._layers.append(_draw)
        return self

    def add_callout(
        self,
        x: float,
        y: float,
        text: str,
        *,
        dx: float = 0.0,
        dy: float = 0.0,
        anchor: str = "start",
        leader_role: str | None = None,
        leader_dx: float = 0.0,
        leader_dy: float = 0.0,
        muted: bool = False,
        clamp: bool = True,
    ) -> "Chart":
        self._all_texts.append(text)
        cls = "ec-annot-muted" if muted else "ec-annot"
        fsize = 12.0 if muted else 12.5
        leader_color = self.theme.color(leader_role) if leader_role else None

        def _draw(x_sc: LinearScale, y_sc: LinearScale, xl: float, xr: float, yt: float, yb: float):
            px, py = x_sc.map(x), y_sc.map(y)
            tx = px + dx
            ty = py + dy
            if clamp:
                # Guarantee callout never intrudes into title/subtitle/legend header
                ty = max(yt + 16.0, min(yb - 6.0, ty))
                tx = max(xl + 4.0, min(xr - 4.0, tx))
            self._callout_y_positions.append((text, ty))
            u: list[str] = []
            if leader_color:
                lx1 = max(xl, min(xr, px))
                ly1 = max(yt + 2.0, min(yb - 2.0, py - 4.0))
                lx2 = max(xl + 2.0, min(xr - 2.0, px + leader_dx))
                ly2 = max(yt + 12.0, min(yb - 4.0, py + leader_dy))
                u.append(
                    f'<line x1="{lx1:.1f}" y1="{ly1:.1f}" '
                    f'x2="{lx2:.1f}" y2="{ly2:.1f}" '
                    f'stroke="{leader_color}" stroke-width="1.2"/>'
                )
            u.append(
                render_rich_svg(
                    text,
                    tx,
                    ty,
                    text_class=cls,
                    font_size=fsize,
                    anchor=anchor,
                    muted=muted,
                )
            )
            return [], u

        self._layers.append(_draw)
        return self

    def add_top_label(
        self,
        x: float,
        text: str,
        *,
        dx: float = -8.0,
        dy: float = 18.0,
        anchor: str = "end",
    ) -> "Chart":
        self._all_texts.append(text)

        def _draw(x_sc: LinearScale, _y_sc: LinearScale, _xl: float, _xr: float, yt: float, _yb: float):
            px = x_sc.map(x)
            ty = max(yt + 16.0, yt + dy)
            self._callout_y_positions.append((text, ty))
            return [], [
                render_rich_svg(
                    text,
                    px + dx,
                    ty,
                    text_class="ec-annot",
                    font_size=12.5,
                    anchor=anchor,
                )
            ]

        self._layers.append(_draw)
        return self

    def add_custom(self, fn: DrawCallback) -> "Chart":
        """Register an escape-hatch drawing callback returning (clipped, unclipped)."""
        self._layers.append(fn)
        return self

    def _render_legend(self, x_start: float, y: float) -> tuple[list[str], float]:
        parts: list[str] = []
        cx = x_start
        cy = y
        max_x = self.theme.width - 24.0
        for item in self._legend_items:
            label = str(item["label"])
            kind = item["kind"]
            color = item["color"]
            glyph_w = 24.0
            item_w = glyph_w + measure_rich_width(label, font_size=13.0) + 20.0
            if cx > x_start and cx + item_w > max_x:
                cx = x_start
                cy += self.theme.legend_row_height

            if kind == "line":
                dash = ' class="ec-line-dashed"' if item.get("dashed") else ""
                parts.append(
                    f'<line{dash} x1="{cx:.1f}" y1="{cy - 4:.1f}" x2="{cx + 18:.1f}" y2="{cy - 4:.1f}" '
                    f'stroke="{color}" stroke-width="2.4" stroke-linecap="round"/>'
                )
            elif kind == "band":
                parts.append(
                    f'<rect x="{cx:.1f}" y="{cy - 10:.1f}" width="18" height="11" rx="2" '
                    f'fill="{color}" fill-opacity="0.22" stroke="{color}" stroke-width="1"/>'
                )
            elif kind == "dot":
                parts.append(
                    f'<circle cx="{cx + 9.0:.1f}" cy="{cy - 4.0:.1f}" r="4.2" '
                    f'fill="{color}" fill-opacity="0.55" stroke="{color}" stroke-width="1"/>'
                )
            elif kind == "ref":
                parts.append(
                    f'<line class="ec-ref-line" x1="{cx + 9.0:.1f}" y1="{cy - 11:.1f}" '
                    f'x2="{cx + 9.0:.1f}" y2="{cy + 2:.1f}" stroke="{color}"/>'
                )
            else:
                glyph_name = "triangle" if kind == "tri" else kind
                asset = self._register_glyph(glyph_name)
                parts.append(
                    use_glyph(
                        asset.symbol_id,
                        cx + 9.0,
                        cy - 4.0,
                        11.0,
                        color=color,
                        fill_var=item.get("fill"),
                    )
                )

            parts.append(
                render_rich_svg(
                    label,
                    cx + glyph_w,
                    cy,
                    text_class="ec-legend-text",
                    font_size=13.0,
                )
            )
            cx += item_w
        return parts, cy

    def render(self) -> str:
        """Assemble the self-contained inline SVG string with MathJax paths and layout checks."""
        if self.strict_math:
            for t in self._all_texts:
                bare = find_bare_math(t)
                if bare:
                    raise ValueError(
                        f"Bare math symbol(s) {bare} found outside $...$ in chart text: {t!r}"
                    )

        prefetch_math(self._all_texts)
        self._callout_y_positions.clear()

        w, h = self.theme.width, self.theme.height
        parts: list[str] = [
            f'<rect class="ec-card-bg" width="{int(w)}" height="{int(h)}" rx="{int(self.theme.card_radius)}"/>'
        ]

        parts.append(
            render_rich_svg(self.title, 28.0, 30.0, text_class="ec-title", font_size=17.0)
        )
        y_cursor = 50.0
        if self.subtitle:
            parts.append(
                render_rich_svg(
                    self.subtitle,
                    28.0,
                    y_cursor,
                    text_class="ec-subtitle",
                    font_size=12.8,
                    muted=True,
                )
            )
            y_cursor += 21.0

        if self._legend_items:
            leg_parts, leg_bottom = self._render_legend(28.0, y_cursor + 2.0)
            parts.extend(leg_parts)
            y_top = leg_bottom + 20.0
        else:
            y_top = y_cursor + 12.0

        y_bot = h - self.theme.margin_bottom
        x_scale = LinearScale(self.x_min, self.x_max, self.x_left, self.x_right)
        y_scale = LinearScale(self.y_min, self.y_max, y_bot, y_top)

        for t in self.y_ticks:
            py = y_scale.map(t)
            parts.append(
                f'<line class="ec-grid" x1="{self.x_left:.1f}" x2="{self.x_right:.1f}" y1="{py:.2f}" y2="{py:.2f}"/>'
            )
            parts.append(
                f'<text class="ec-tick" x="{self.x_left - 9:.1f}" y="{py:.2f}" dy="0.35em" text-anchor="end">{fmt_tick(t)}</text>'
            )

        if self.x_grid:
            for t in self.x_ticks:
                px = x_scale.map(t)
                parts.append(
                    f'<line class="ec-grid-subtle" x1="{px:.2f}" x2="{px:.2f}" y1="{y_top:.1f}" y2="{y_bot:.1f}"/>'
                )

        clip_hash = hashlib.sha1(
            f"{self.title}|{self.subtitle}|{self.x_left}|{y_top}".encode("utf-8")
        ).hexdigest()[:8]
        clip_id = f"ec-clip-{clip_hash}"

        clipped_parts: list[str] = []
        unclipped_parts: list[str] = []
        for fn in self._layers:
            c, u = fn(x_scale, y_scale, self.x_left, self.x_right, y_top, y_bot)
            clipped_parts.extend(c)
            unclipped_parts.extend(u)

        # Layout gate: verify zero callouts intrude into header/legend band
        for lbl, cy in self._callout_y_positions:
            if cy < y_top + 10.0:
                raise ValueError(
                    f"Callout {lbl!r} at y={cy:.1f} intrudes into header (y_top={y_top:.1f})"
                )

        parts.append(f'<g clip-path="url(#{clip_id})">')
        parts.extend(clipped_parts)
        parts.append("</g>")

        parts.append(
            f'<line class="ec-axis" x1="{self.x_left:.1f}" x2="{self.x_left:.1f}" y1="{y_top:.1f}" y2="{y_bot:.1f}"/>'
        )
        parts.append(
            f'<line class="ec-axis" x1="{self.x_left:.1f}" x2="{self.x_right:.1f}" y1="{y_bot:.1f}" y2="{y_bot:.1f}"/>'
        )

        for t in self.x_ticks:
            px = x_scale.map(t)
            parts.append(
                f'<line class="ec-axis" x1="{px:.2f}" x2="{px:.2f}" y1="{y_bot:.1f}" y2="{y_bot + 4.5:.1f}"/>'
            )
            parts.append(
                f'<text class="ec-tick" x="{px:.2f}" y="{y_bot + 19:.1f}" text-anchor="middle">{fmt_tick(t)}</text>'
            )

        if self.x_label:
            parts.append(
                render_rich_svg(
                    self.x_label,
                    (self.x_left + self.x_right) / 2.0,
                    h - 13.0,
                    text_class="ec-axis-label",
                    font_size=13.5,
                    anchor="middle",
                )
            )
        if self.y_label:
            ym = (y_top + y_bot) / 2.0
            parts.append(
                render_rich_svg(
                    self.y_label,
                    0.0,
                    0.0,
                    text_class="ec-axis-label",
                    font_size=13.5,
                    anchor="middle",
                    transform=f"translate(20, {ym:.1f}) rotate(-90)",
                )
            )

        parts.extend(unclipped_parts)

        symbol_defs = "".join(g.as_symbol() for g in self._used_glyphs.values())
        defs = (
            f'<defs><clipPath id="{clip_id}">'
            f'<rect x="{self.x_left:.1f}" y="{y_top:.1f}" '
            f'width="{self.x_right - self.x_left:.1f}" height="{y_bot - y_top:.1f}"/>'
            f"</clipPath>{symbol_defs}</defs>"
        )
        css_text = self.theme.combined_css()
        inner = "\n  ".join(parts)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" data-htd-inline="1" '
            f'viewBox="0 0 {int(w)} {int(h)}" width="{int(w)}" height="{int(h)}" class="ec-svg">\n'
            f"  <style>\n{css_text}\n  </style>\n"
            f"  {defs}\n"
            f"  {inner}\n"
            f"</svg>\n"
        )

    def save_svg(self, path: Path | str) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.render(), encoding="utf-8")
        return out
