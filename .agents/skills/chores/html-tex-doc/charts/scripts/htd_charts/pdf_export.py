"""Single-page vector PDF exporter using an external HTML print template."""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .theme import TEMPLATES_DIR, Theme

DEFAULT_PRINT_TEMPLATE = TEMPLATES_DIR / "pdf-print" / "pdf_print.html"
_VIEWBOX_RE = re.compile(r'viewBox="0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"')


def _infer_dimensions(svg_text: str, fallback_w: int, fallback_h: int) -> tuple[int, int]:
    m = _VIEWBOX_RE.search(svg_text)
    if not m:
        return fallback_w, fallback_h
    return int(round(float(m.group(1)))), int(round(float(m.group(2))))


def export_pdfs_via_chrome(
    svg_paths: list[Path],
    *,
    theme: str | Theme = "editorial-academic",
    template_path: Path | None = None,
    chrome_bin: str = "google-chrome",
) -> list[Path]:
    """Export each SVG to a zero-margin single-page vector PDF via headless Chrome."""
    resolved_theme = theme if isinstance(theme, Theme) else Theme(theme)
    tpl_file = Path(template_path) if template_path else DEFAULT_PRINT_TEMPLATE
    if not tpl_file.exists():
        raise FileNotFoundError(f"Missing PDF print HTML template: {tpl_file}")
    tpl_text = tpl_file.read_text(encoding="utf-8")

    tmp_root = Path(tempfile.mkdtemp(prefix="htd_charts_pdf_"))
    profile_dir = tmp_root / "chrome_profile"
    html_dir = tmp_root / "html"
    profile_dir.mkdir(parents=True, exist_ok=True)
    html_dir.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []
    try:
        for svg_path in svg_paths:
            svg_p = Path(svg_path)
            pdf_path = svg_p.with_suffix(".pdf")
            svg_text = svg_p.read_text(encoding="utf-8")
            w, h = _infer_dimensions(
                svg_text, int(resolved_theme.width), int(resolved_theme.height)
            )
            html_doc = (
                tpl_text.replace("__WIDTH__", str(w))
                .replace("__HEIGHT__", str(h))
                .replace("__BACKGROUND__", resolved_theme.pdf_background)
                .replace("__SVG_CONTENT__", svg_text)
            )
            html_file = html_dir / f"{svg_p.parent.name}_{svg_p.stem}.html"
            html_file.write_text(html_doc, encoding="utf-8")

            cmd = [
                chrome_bin,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                f"--user-data-dir={profile_dir}",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path}",
                html_file.as_uri(),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode != 0 or not pdf_path.exists():
                raise RuntimeError(
                    f"Chrome PDF export failed for {svg_p}: rc={res.returncode}\n{res.stderr}"
                )

            info = subprocess.run(
                ["pdfinfo", str(pdf_path)], capture_output=True, text=True, check=True
            )
            if not re.search(r"Pages:\s+1\b", info.stdout):
                raise RuntimeError(f"Expected single-page PDF for {pdf_path}, got:\n{info.stdout}")
            exported.append(pdf_path)
    finally:
        time.sleep(0.1)
        shutil.rmtree(tmp_root, ignore_errors=True)
    return exported
