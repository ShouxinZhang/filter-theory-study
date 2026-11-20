#!/usr/bin/env python3
"""Paper chart builder skeleton calling the decoupled htd_charts engine."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Point to .agents/skills/chores/html-tex-doc/charts/scripts
CHARTS_SCRIPTS = Path("__CHARTS_SCRIPTS_DIR__")
if str(CHARTS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CHARTS_SCRIPTS))

from htd_charts import Chart, export_pdfs_via_chrome  # noqa: E402


def main() -> None:
    base = Path(__file__).resolve().parent
    sim = json.loads((base / "sim_data.json").read_text(encoding="utf-8"))
    out_dir = base / "figs"
    out_dir.mkdir(parents=True, exist_ok=True)

    chart = (
        Chart(
            title="示例曲线对比",
            subtitle="时间步 $k = 0 \\dots 10$",
            theme="editorial-academic",
            x_domain=(0.0, 10.0),
            y_domain=(-1.2, 1.2),
            x_ticks=[0, 2, 4, 6, 8, 10],
            y_ticks=[-1.0, -0.5, 0.0, 0.5, 1.0],
            x_label="时间步 $k$",
            y_label="状态 $x_k$",
        )
        .add_legend("主曲线", kind="line", role="primary")
        .add_line(sim["x"], sim["y"], role="primary")
    )

    svg_path = out_dir / "fig1.svg"
    chart.save_svg(svg_path)
    export_pdfs_via_chrome([svg_path])
    print(f"Rendered {svg_path} and {svg_path.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
