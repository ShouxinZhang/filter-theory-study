"""External theme pack and SVG glyph asset loader.

Loads all CSS styles and vector glyph fragments from static asset directories
so zero CSS rules or SVG marker paths are hardcoded in Python.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CHARTS_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = CHARTS_ROOT / "assets"
THEMES_DIR = ASSETS_DIR / "themes"
GLYPHS_DIR = ASSETS_DIR / "glyphs"
TEMPLATES_DIR = CHARTS_ROOT / "references" / "templates"

_SVG_ROOT_RE = re.compile(
    r"<svg\b[^>]*\bviewBox=[\"']([^\"']+)[\"'][^>]*>(.*?)</svg>",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class GlyphAsset:
    name: str
    symbol_id: str
    view_box: str
    inner_xml: str

    def as_symbol(self) -> str:
        return f'<symbol id="{self.symbol_id}" viewBox="{self.view_box}">{self.inner_xml}</symbol>'


class Theme:
    """Resolved chart theme pack (base.css + theme tokens.css + optional override)."""

    def __init__(
        self,
        name: str = "editorial-academic",
        *,
        theme_dirs: list[Path] | None = None,
        glyph_dirs: list[Path] | None = None,
        override_css: Path | None = None,
    ) -> None:
        self.name = name
        self.theme_dirs = list(theme_dirs or []) + [THEMES_DIR]
        self.glyph_dirs = list(glyph_dirs or []) + [GLYPHS_DIR]
        self.override_css = Path(override_css) if override_css else None

        self.theme_path = self._resolve_theme_dir(name)
        meta_file = self.theme_path / "theme.json"
        if not meta_file.exists():
            raise FileNotFoundError(f"Missing theme metadata: {meta_file}")
        self.meta: dict[str, Any] = json.loads(meta_file.read_text(encoding="utf-8"))

        self.width = float(self.meta.get("width", 880))
        self.height = float(self.meta.get("height", 480))
        self.card_radius = float(self.meta.get("card_radius", 8))
        self.pdf_background = str(self.meta.get("pdf_background", "#FAF9F5"))
        margins = self.meta.get("margins", {})
        self.margin_left = float(margins.get("left", 74))
        self.margin_right = float(margins.get("right", 28))
        self.margin_bottom = float(margins.get("bottom", 54))
        legend = self.meta.get("legend", {})
        self.legend_row_height = float(legend.get("row_height", 20))
        self.legend_cjk_px = float(legend.get("cjk_px", 13.5))
        self.legend_ascii_px = float(legend.get("ascii_px", 7.4))
        self.palette: dict[str, str] = dict(self.meta.get("palette", {}))
        self._glyph_cache: dict[str, GlyphAsset] = {}

    def _resolve_theme_dir(self, name: str) -> Path:
        direct = Path(name)
        if direct.is_dir() and (direct / "theme.json").exists():
            return direct
        for root in self.theme_dirs:
            cand = root / name
            if cand.is_dir() and (cand / "theme.json").exists():
                return cand
        raise FileNotFoundError(f"Chart theme '{name}' not found in {self.theme_dirs}")

    def color(self, role_or_value: str) -> str:
        """Resolve a semantic role (e.g. 'primary', 'fg') to its CSS value."""
        return self.palette.get(role_or_value, role_or_value)

    def combined_css(self) -> str:
        """Load base.css + theme tokens.css + optional paper override.css."""
        chunks: list[str] = []
        base_css = ASSETS_DIR / "base.css"
        if base_css.exists():
            chunks.append(base_css.read_text(encoding="utf-8").strip())
        tokens_css = self.theme_path / "tokens.css"
        if tokens_css.exists():
            chunks.append(tokens_css.read_text(encoding="utf-8").strip())
        extra_theme_css = self.theme_path / "chart.css"
        if extra_theme_css.exists():
            chunks.append(extra_theme_css.read_text(encoding="utf-8").strip())
        if self.override_css and self.override_css.exists():
            chunks.append(self.override_css.read_text(encoding="utf-8").strip())
        return "\n".join(c for c in chunks if c)

    def load_glyph(self, name: str) -> GlyphAsset:
        """Load an external SVG glyph fragment from assets/glyphs/<name>.svg."""
        if name in self._glyph_cache:
            return self._glyph_cache[name]
        for root in self.glyph_dirs:
            cand = root / f"{name}.svg"
            if cand.exists():
                raw = cand.read_text(encoding="utf-8").strip()
                m = _SVG_ROOT_RE.search(raw)
                if not m:
                    raise ValueError(f"Glyph SVG must have a viewBox: {cand}")
                asset = GlyphAsset(
                    name=name,
                    symbol_id=f"ec-glyph-{name}",
                    view_box=m.group(1).strip(),
                    inner_xml=m.group(2).strip(),
                )
                self._glyph_cache[name] = asset
                return asset
        raise FileNotFoundError(f"Glyph '{name}.svg' not found in {self.glyph_dirs}")


def list_available_themes(extra_dirs: list[Path] | None = None) -> list[dict[str, str]]:
    """Return metadata summaries of all installed theme packs."""
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for root in list(extra_dirs or []) + [THEMES_DIR]:
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            meta_file = d / "theme.json"
            if d.is_dir() and meta_file.exists() and d.name not in seen:
                seen.add(d.name)
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                out.append(
                    {
                        "name": str(meta.get("name", d.name)),
                        "path": str(d),
                        "description": str(meta.get("description", "")),
                    }
                )
    return out
