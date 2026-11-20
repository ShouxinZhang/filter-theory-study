"""Decoupled academic & editorial SVG/PDF chart engine for html-tex-doc."""
from .layout import Chart
from .math_text import (
    esc,
    find_bare_math,
    measure_rich_width,
    prefetch_math,
    render_rich_svg,
    split_math_runs,
    text_width_px,
)
from .pdf_export import export_pdfs_via_chrome
from .primitives import build_area_path, build_band_path, build_polyline, use_glyph
from .scales import LinearScale, fmt_tick
from .theme import (
    ASSETS_DIR,
    CHARTS_ROOT,
    GLYPHS_DIR,
    TEMPLATES_DIR,
    THEMES_DIR,
    Theme,
    list_available_themes,
)

__all__ = [
    "ASSETS_DIR",
    "CHARTS_ROOT",
    "GLYPHS_DIR",
    "TEMPLATES_DIR",
    "THEMES_DIR",
    "Chart",
    "LinearScale",
    "Theme",
    "build_area_path",
    "build_band_path",
    "build_polyline",
    "esc",
    "export_pdfs_via_chrome",
    "find_bare_math",
    "fmt_tick",
    "list_available_themes",
    "measure_rich_width",
    "prefetch_math",
    "render_rich_svg",
    "split_math_runs",
    "text_width_px",
    "use_glyph",
]
