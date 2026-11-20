"""Unit, MathJax-rendering, layout-guard, and static-decoupling tests for html-tex-doc/charts."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHARTS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = CHARTS_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from htd_charts import (
    Chart,
    LinearScale,
    Theme,
    find_bare_math,
    fmt_tick,
    list_available_themes,
    render_rich_svg,
)


class TestChartsDecoupling(unittest.TestCase):
    def test_no_hardcoded_html_or_css_in_python_engine(self) -> None:
        """Strictly forbid hardcoded HTML/CSS rules inside Python engine modules."""
        forbidden = ("<!doctype", "@page", "font-family:", "stroke-dasharray:", "background:")
        engine_dir = SCRIPTS_DIR / "htd_charts"
        py_files = sorted(engine_dir.glob("*.py"))
        self.assertGreaterEqual(len(py_files), 6)
        for py in py_files:
            src = py.read_text(encoding="utf-8").lower()
            for token in forbidden:
                self.assertNotIn(token, src, f"Hardcoded '{token}' found in {py.name}")

    def test_theme_loading_and_override(self) -> None:
        themes = list_available_themes()
        names = [t["name"] for t in themes]
        self.assertIn("editorial-academic", names)

        with tempfile.TemporaryDirectory() as td:
            override = Path(td) / "paper.css"
            override.write_text(".ec-svg { --ec-primary: #123456; }\n", encoding="utf-8")
            theme = Theme("editorial-academic", override_css=override)
            css = theme.combined_css()
            self.assertIn("--ec-font-math", css)
            self.assertIn("--ec-primary: #123456;", css)
            self.assertEqual(theme.color("primary"), "var(--ec-primary)")

    def test_external_glyph_loading(self) -> None:
        theme = Theme("editorial-academic")
        for gname in ("star", "triangle", "observer"):
            g = theme.load_glyph(gname)
            self.assertEqual(g.symbol_id, f"ec-glyph-{gname}")
            self.assertIn("<symbol ", g.as_symbol())

    def test_mathjax_svg_vector_rendering_and_bare_math_guard(self) -> None:
        out = render_rich_svg(
            r"缩放参数 $\kappa = 1$ 与误差 ($\times 10^{-3}$)",
            28.0,
            30.0,
            text_class="ec-title",
            font_size=17.0,
        )
        self.assertIn("<path ", out)
        self.assertIn('fill="currentColor"', out)
        self.assertNotIn("κ", out)

        self.assertTrue(find_bare_math("缩放参数 κ"))
        self.assertTrue(find_bare_math("状态 x_5"))
        self.assertEqual(find_bare_math(r"缩放参数 $\kappa$ 与状态 $x_5$"), [])

    def test_strict_math_rejects_bare_symbols(self) -> None:
        c = Chart("缩放参数 κ", x_domain=(0, 1), y_domain=(0, 1))
        with self.assertRaises(ValueError):
            c.render()

    def test_callout_clamping_prevents_header_collision(self) -> None:
        c = (
            Chart(
                r"参数 $x_5$ 收敛",
                subtitle=r"真实值 $x_5 = 0.6932$",
                x_domain=(0, 80),
                y_domain=(-0.2, 1.3),
                x_ticks=[0, 40, 80],
                y_ticks=[0.0, 0.6, 1.2],
            )
            .add_legend("曲线", kind="line", role="primary")
            # Deliberately place an out-of-range peak with negative dy
            .add_callout(17.0, 1.42, r"超调 ($1.42$)", dx=14, dy=-20, leader_role="secondary")
        )
        svg = c.render()
        self.assertIn('data-htd-inline="1"', svg)
        self.assertIn("<path ", svg)
        # All callout y positions must stay strictly below header y_top
        for _lbl, cy in c._callout_y_positions:
            self.assertGreaterEqual(cy, 100.0)

    def test_scales_and_ticks(self) -> None:
        sc = LinearScale(0.0, 10.0, 100.0, 200.0)
        self.assertAlmostEqual(sc.map(5.0), 150.0)
        self.assertEqual(fmt_tick(-0.0), "0")
        self.assertEqual(fmt_tick(0.30000000000000004), "0.3")

    def test_chart_assembly_and_unique_clip_ids(self) -> None:
        c1 = (
            Chart(
                "图一",
                subtitle=r"$k = 0\dots 10$",
                x_domain=(0, 10),
                y_domain=(-1, 1),
                x_ticks=[0, 5, 10],
                y_ticks=[-1, 0, 1],
                x_label=r"时间步 $k$",
                y_label=r"状态 $x_k$",
            )
            .add_legend("主曲线", kind="line", role="primary")
            .add_legend("真值", kind="star", role="fg")
            .add_band([0, 5, 10], [-0.5, -0.2, -0.4], [0.5, 0.8, 0.6], role="primary")
            .add_line([0, 5, 10], [0.0, 0.3, 0.1], role="primary")
            .add_markers([0, 5, 10], [0.0, 0.3, 0.1], glyph="star", role="fg")
        )
        svg1 = c1.render()
        self.assertIn('data-htd-inline="1"', svg1)
        self.assertIn('id="ec-glyph-star"', svg1)
        self.assertIn('href="#ec-glyph-star"', svg1)
        self.assertIn("<path ", svg1)

        c2 = Chart("图二", x_domain=(0, 10), y_domain=(0, 1), x_left=82.0)
        svg2 = c2.render()
        self.assertNotEqual(
            svg1.split('clipPath id="')[1].split('"')[0],
            svg2.split('clipPath id="')[1].split('"')[0],
        )

    def test_cli_scaffolding_commands(self) -> None:
        cli = SCRIPTS_DIR / "charts_cli.py"
        res = subprocess.run([sys.executable, str(cli), "themes"], capture_output=True, text=True, check=True)
        self.assertIn("editorial-academic", res.stdout)

        with tempfile.TemporaryDirectory() as td:
            t_dir = Path(td) / "my-theme"
            subprocess.run(
                [sys.executable, str(cli), "init-theme", "my-theme", "--out", str(t_dir)],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertTrue((t_dir / "tokens.css").exists())
            self.assertIn('"my-theme"', (t_dir / "theme.json").read_text(encoding="utf-8"))

            p_dir = Path(td) / "paper_charts"
            subprocess.run(
                [sys.executable, str(cli), "init-paper", str(p_dir)],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertTrue((p_dir / "simulate.py").exists())
            self.assertTrue((p_dir / "build_charts.py").exists())


if __name__ == "__main__":
    unittest.main()
