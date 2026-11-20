#!/usr/bin/env python3
"""Black-box CLI for html-tex-doc/charts sub-skill.

Subcommands:
  themes       List available chart theme packs
  init-theme   Create a new theme pack from references/templates/chart-theme
  init-paper   Scaffold simulate.py + build_charts.py from references/templates/paper-charts
  export-pdf   Batch-export SVG files to single-page vector PDFs via Chrome
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from htd_charts import TEMPLATES_DIR, THEMES_DIR, export_pdfs_via_chrome, list_available_themes


def cmd_themes(_args: argparse.Namespace) -> int:
    for item in list_available_themes():
        print(f"{item['name']}\t{item['path']}\t{item['description']}")
    return 0


def cmd_init_theme(args: argparse.Namespace) -> int:
    dst = Path(args.out) if args.out else (THEMES_DIR / args.name)
    if dst.exists():
        print(f"Error: target theme directory already exists: {dst}", file=sys.stderr)
        return 1
    src = TEMPLATES_DIR / "chart-theme"
    shutil.copytree(src, dst)
    meta_file = dst / "theme.json"
    meta_file.write_text(
        meta_file.read_text(encoding="utf-8").replace("__THEME_NAME__", args.name),
        encoding="utf-8",
    )
    print(f"Created theme pack: {dst}")
    return 0


def cmd_init_paper(args: argparse.Namespace) -> int:
    dst = Path(args.dir)
    dst.mkdir(parents=True, exist_ok=True)
    src = TEMPLATES_DIR / "paper-charts"
    for name in ("simulate.py", "build_charts.py"):
        target = dst / name
        if target.exists() and not args.force:
            print(f"Skip existing: {target} (use --force to overwrite)")
            continue
        text = (src / name).read_text(encoding="utf-8").replace(
            "__CHARTS_SCRIPTS_DIR__", str(SCRIPTS_DIR)
        )
        target.write_text(text, encoding="utf-8")
        target.chmod(0o755)
        print(f"Created: {target}")
    return 0


def cmd_export_pdf(args: argparse.Namespace) -> int:
    svgs: list[Path] = []
    for raw in args.paths:
        p = Path(raw)
        if p.is_dir():
            svgs.extend(sorted(p.glob("*.svg")))
        elif p.is_file():
            svgs.append(p)
    if not svgs:
        print("No SVG files found.", file=sys.stderr)
        return 1
    pdfs = export_pdfs_via_chrome(svgs, theme=args.theme)
    print(f"Exported {len(pdfs)} single-page vector PDFs.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="html-tex-doc/charts CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("themes", help="List installed chart theme packs")

    p_theme = sub.add_parser("init-theme", help="Create a new chart theme pack from template")
    p_theme.add_argument("name", help="Theme pack name")
    p_theme.add_argument("--out", help="Optional custom output directory")

    p_paper = sub.add_parser("init-paper", help="Scaffold simulate.py and build_charts.py")
    p_paper.add_argument("dir", help="Target directory for paper chart scripts")
    p_paper.add_argument("--force", action="store_true", help="Overwrite existing files")

    p_pdf = sub.add_parser("export-pdf", help="Export SVG file(s) or directory to vector PDFs")
    p_pdf.add_argument("paths", nargs="+", help="SVG files or directories")
    p_pdf.add_argument("--theme", default="editorial-academic", help="Theme name for PDF background")

    args = ap.parse_args()
    handlers = {
        "themes": cmd_themes,
        "init-theme": cmd_init_theme,
        "init-paper": cmd_init_paper,
        "export-pdf": cmd_export_pdf,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
