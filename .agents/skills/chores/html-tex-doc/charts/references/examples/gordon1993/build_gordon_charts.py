#!/usr/bin/env python3
"""Gordon, Salmond, & Smith (1993) bilingual chart builder example.

Uses explicit $...$ MathJax vector rendering via htd_charts with zero CSS,
HTML, or SVG glyph path hardcoding.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

CHARTS_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(CHARTS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CHARTS_SCRIPTS))

from htd_charts import Chart, export_pdfs_via_chrome  # noqa: E402

FORBIDDEN_ZH_PATTERN = re.compile(
    r"(EKF|Kalman|Bayesian|Gaussian|Bootstrap|卡尔曼|高斯|贝叶斯|戈登)",
    re.IGNORECASE,
)


def build_all_charts(sim: dict[str, Any], lang: str, theme: str = "editorial-academic") -> dict[str, str]:
    """Build all 11 SVG strings for the requested language ('en' or 'zh')."""
    zh = lang == "zh"
    e1 = sim["example_1"]
    e2 = sim["example_2"]
    svgs: dict[str, str] = {}

    k_all = [float(k) for k in e1["k_all"]]
    x_true1 = [float(v) for v in e1["x_true"]]

    # Fig 1: 1D true state trajectory
    svgs["fig1"] = (
        Chart(
            "一维非线性非平稳状态轨迹" if zh else "1D Nonlinear Non-Stationary State Trajectory",
            subtitle=(
                r"真实状态演化 ($k = 0\dots 50,\ x_0 = 0.1$)"
                if zh
                else r"True state evolution ($k = 0\dots 50,\ x_0 = 0.1$)"
            ),
            theme=theme,
            x_domain=(0, 50),
            y_domain=(-25, 25),
            x_ticks=[0, 10, 20, 30, 40, 50],
            y_ticks=[-20, -10, 0, 10, 20],
            x_label=r"时间步 $k$" if zh else r"Time step $k$",
            y_label=r"状态 $x_k$" if zh else r"State $x_k$",
        )
        .add_legend(r"真实状态 $x_k$" if zh else r"True state $x_k$", kind="star", role="fg")
        .add_legend("状态连线" if zh else "State trajectory", kind="line", role="accent")
        .add_line(k_all, x_true1, role="accent", thin=True)
        .add_markers(k_all, x_true1, glyph="star", size=8.6, role="fg")
        .render()
    )

    # Fig 2: 1D EKF
    ekf1_mean = [float(v) for v in e1["ekf"]["mean"]]
    ekf1_lo = [float(v) for v in e1["ekf"]["lo95"]]
    ekf1_hi = [float(v) for v in e1["ekf"]["hi95"]]
    svgs["fig2"] = (
        Chart(
            "一阶线性化滤波状态估计与 95% 概率区间" if zh else "EKF State Estimate and 95% Probability Interval",
            subtitle="一维算例 · 95% 区间覆盖率 30.0% (15/50)" if zh else "1D Example · 95% interval coverage 30.0% (15/50)",
            theme=theme,
            x_domain=(0, 50),
            y_domain=(-40, 40),
            x_ticks=[0, 10, 20, 30, 40, 50],
            y_ticks=[-40, -20, 0, 20, 40],
            x_label=r"时间步 $k$" if zh else r"Time step $k$",
            y_label=r"状态 $x_k$" if zh else r"State $x_k$",
        )
        .add_legend("一阶线性化后验均值" if zh else "EKF posterior mean", kind="line", role="secondary")
        .add_legend("95% 概率区间" if zh else "95% probability interval", kind="band", role="secondary")
        .add_legend("真实状态" if zh else "True state", kind="star", role="fg")
        .add_band(k_all, ekf1_lo, ekf1_hi, role="secondary", opacity=0.18)
        .add_line(k_all, ekf1_mean, role="secondary")
        .add_markers(k_all, x_true1, glyph="star", size=8.4, role="fg")
        .render()
    )

    # Fig 3: 1D BPF
    bpf1_mean = [float(v) for v in e1["bpf"]["mean"]]
    bpf1_lo = [float(v) for v in e1["bpf"]["lo95"]]
    bpf1_hi = [float(v) for v in e1["bpf"]["hi95"]]
    svgs["fig3"] = (
        Chart(
            "自举粒子滤波状态估计与 95% 概率区间" if zh else "Bootstrap Filter State Estimate and 95% Interval",
            subtitle=(
                r"一维算例 ($N = 500$) · 95% 区间覆盖率 90.0% (45/50)"
                if zh
                else r"1D Example ($N = 500$) · 95% interval coverage 90.0% (45/50)"
            ),
            theme=theme,
            x_domain=(0, 50),
            y_domain=(-40, 40),
            x_ticks=[0, 10, 20, 30, 40, 50],
            y_ticks=[-40, -20, 0, 20, 40],
            x_label=r"时间步 $k$" if zh else r"Time step $k$",
            y_label=r"状态 $x_k$" if zh else r"State $x_k$",
        )
        .add_legend("自举粒子滤波后验均值" if zh else "Bootstrap filter mean", kind="line", role="primary")
        .add_legend("95% 概率区间" if zh else "95% quantile interval", kind="band", role="primary")
        .add_legend("真实状态" if zh else "True state", kind="star", role="fg")
        .add_band(k_all, bpf1_lo, bpf1_hi, role="primary", opacity=0.20)
        .add_line(k_all, bpf1_mean, role="primary")
        .add_markers(k_all, x_true1, glyph="star", size=8.4, role="fg")
        .render()
    )

    # Fig 4: k = 21 Posterior density comparison
    k21 = e1["k21_density"]
    gx = [float(v) for v in k21["grid_x"]]
    kde = [float(v) for v in k21["bpf_kde"]]
    epdf = [float(v) for v in k21["ekf_pdf"]]
    x21_true = float(k21["x_true"])
    y21_obs = float(k21["y_obs"])
    sec_x = float(k21["bpf_secondary_mode_x"])
    sec_d = float(k21["bpf_secondary_mode_density"])
    ekf_m = float(k21["ekf_mean"])

    svgs["fig4"] = (
        Chart(
            r"时刻 $k = 21$ 估计后验密度对比" if zh else r"Estimated Posterior Density at $k = 21$",
            subtitle=(
                f"观测 $y_{{21}} = {y21_obs:.2f}$ 诱发对称双峰 · 真实状态 $x_{{21}} = {x21_true:.2f}$"
                if zh
                else f"Observation $y_{{21}} = {y21_obs:.2f}$ induces symmetric bimodality · True $x_{{21}} = {x21_true:.2f}$"
            ),
            theme=theme,
            x_domain=(-40, 40),
            y_domain=(0.0, 0.22),
            x_ticks=[-40, -30, -20, -10, 0, 10, 20, 30, 40],
            y_ticks=[0.0, 0.05, 0.10, 0.15, 0.20],
            x_label=r"状态 $x_{21}$" if zh else r"State $x_{21}$",
            y_label="后验概率密度" if zh else "Posterior density",
        )
        .add_legend("自举样本核密度" if zh else "Bootstrap KDE", kind="line", role="primary")
        .add_legend("一阶线性化正态近似" if zh else "EKF normal approximation", kind="line", role="secondary", dashed=True)
        .add_legend("真实状态" if zh else "True state", kind="ref", role="fg")
        .add_area(gx, kde, baseline=0.0, role="primary", opacity=0.22)
        .add_line(gx, kde, role="primary")
        .add_line(gx, epdf, role="secondary", dashed=True)
        .add_vline(x21_true, marker_glyph="star", marker_size=10.8, marker_role="fg")
        .add_top_label(
            x21_true,
            f"真实状态 $x_{{21}} = {x21_true:.2f}$" if zh else f"True $x_{{21}} = {x21_true:.2f}$",
        )
        .add_callout(
            sec_x,
            sec_d,
            f"对称次峰 (${sec_x:.1f}$)" if zh else f"Secondary mode (${sec_x:.1f}$)",
            dx=14,
            dy=-32,
            leader_role="primary",
            leader_dx=12,
            leader_dy=-28,
        )
        .add_callout(
            ekf_m,
            max(epdf),
            f"一阶线性化错峰 (${ekf_m:.1f}$)" if zh else f"EKF wrong peak (${ekf_m:.1f}$)",
            dx=10,
            dy=14,
        )
        .render()
    )

    # Example 2 shared arrays
    k2 = [float(k) for k in e2["k_steps"]]
    tx2 = [float(r[0]) for r in e2["x_true"]]
    tvx2 = [float(r[1]) for r in e2["x_true"]]
    ty2 = [float(r[2]) for r in e2["x_true"]]

    bx2 = [float(r[0]) for r in e2["bpf"]["mean"]]
    bvx2 = [float(r[1]) for r in e2["bpf"]["mean"]]
    by2 = [float(r[2]) for r in e2["bpf"]["mean"]]
    bx2_lo = [float(r[0]) for r in e2["bpf"]["lo95"]]
    bx2_hi = [float(r[0]) for r in e2["bpf"]["hi95"]]
    bvx2_lo = [float(r[1]) for r in e2["bpf"]["lo95"]]
    bvx2_hi = [float(r[1]) for r in e2["bpf"]["hi95"]]

    ex2 = [float(r[0]) for r in e2["ekf"]["mean"]]
    evx2 = [float(r[1]) for r in e2["ekf"]["mean"]]
    ey2 = [float(r[2]) for r in e2["ekf"]["mean"]]
    ex2_lo = [float(r[0]) for r in e2["ekf"]["lo95"]]
    ex2_hi = [float(r[0]) for r in e2["ekf"]["hi95"]]
    evx2_lo = [float(r[1]) for r in e2["ekf"]["lo95"]]
    evx2_hi = [float(r[1]) for r in e2["ekf"]["hi95"]]

    # Fig 5: 2D true trajectory
    svgs["fig5"] = (
        Chart(
            "二维纯方位追踪真实目标轨迹" if zh else "Bearings-Only Tracking: True Target Trajectory",
            subtitle=r"原点静止观测站 · 步数 $k = 1\dots 24$" if zh else r"Stationary observer at origin · Time steps $k = 1\dots 24$",
            theme=theme,
            x_domain=(-0.10, 0.20),
            y_domain=(-0.70, 0.80),
            x_ticks=[-0.10, -0.05, 0.0, 0.05, 0.10, 0.15, 0.20],
            y_ticks=[-0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6, 0.8],
            x_label=r"横向坐标 $x$" if zh else r"$x$ position",
            y_label=r"纵向坐标 $y$" if zh else r"$y$ position",
            x_grid=True,
        )
        .add_legend("真实目标位置" if zh else "True target position", kind="triangle", role="fg", fill_role="card")
        .add_legend(r"观测站 $(0, 0)$" if zh else r"Observer $(0, 0)$", kind="observer", role="fg")
        .add_line(tx2, ty2, role="accent", thin=True)
        .add_markers(tx2, ty2, glyph="triangle", size=9.2, role="fg", fill_role="card")
        .add_markers([0.0], [0.0], glyph="observer", size=14.0, role="fg")
        .add_callout(0.0, 0.0, r"观测站 $(0, 0)$" if zh else r"Observer $(0, 0)$", dx=-12, dy=4, anchor="end")
        .add_callout(tx2[0], ty2[0], r"$k = 1$", dx=10, dy=4)
        .add_callout(tx2[-1], ty2[-1], r"$k = 24$", dx=10, dy=4)
        .render()
    )

    # Fig 6: 2D posterior mean trajectory comparison
    svgs["fig6"] = (
        Chart(
            "二维平面后验均值轨迹对比" if zh else r"Posterior Mean Trajectory Comparison ($x$–$y$ Plane)",
            subtitle=(
                "自举粒子滤波紧锁真值 · 一阶线性化滤波飞掠后严重发散"
                if zh
                else "Bootstrap filter locks onto target · EKF diverges after flypast"
            ),
            theme=theme,
            x_domain=(-0.10, 0.34),
            y_domain=(-1.60, 0.90),
            x_ticks=[-0.1, 0.0, 0.1, 0.2, 0.3],
            y_ticks=[-1.5, -1.0, -0.5, 0.0, 0.5],
            x_label=r"横向坐标 $x$" if zh else r"$x$ position",
            y_label=r"纵向坐标 $y$" if zh else r"$y$ position",
            x_grid=True,
        )
        .add_legend("真实目标位置" if zh else "True target", kind="triangle", role="fg", fill_role="card")
        .add_legend("自举粒子滤波" if zh else "Bootstrap filter", kind="line", role="primary")
        .add_legend("一阶线性化滤波" if zh else "EKF", kind="line", role="secondary", dashed=True)
        .add_legend("观测站" if zh else "Observer", kind="observer", role="fg")
        .add_line(ex2, ey2, role="secondary", dashed=True)
        .add_line(bx2, by2, role="primary")
        .add_markers(tx2, ty2, glyph="triangle", size=8.4, role="fg", fill_role="card")
        .add_markers([0.0], [0.0], glyph="observer", size=13.5, role="fg")
        .add_callout(0.0, 0.0, r"观测站 $(0, 0)$" if zh else r"Observer $(0, 0)$", dx=-11, dy=4, anchor="end")
        .add_callout(bx2[-1], by2[-1], r"自举粒子滤波 ($k = 24$)" if zh else r"Bootstrap filter ($k = 24$)", dx=10, dy=4)
        .add_callout(ex2[-1], ey2[-1], r"一阶线性化发散终点 ($k = 24$)" if zh else r"EKF divergent end ($k = 24$)", dx=-10, dy=-6, anchor="end")
        .render()
    )

    # Fig 7: k = 24 posterior scatter
    pts500 = e2["bpf"]["k24_samples_500_xy"]
    sxs = [float(p[0]) for p in pts500]
    sys_ = [float(p[1]) for p in pts500]
    svgs["fig7"] = (
        Chart(
            r"时刻 $k = 24$ 自举后验粒子位置散点" if zh else r"Bootstrap Posterior Position Samples at $k = 24$",
            subtitle=(
                "抽取 500 个后验样本 · 沿视线径向拉长并向右下偏斜"
                if zh
                else "500 samples from posterior · Elongated radially along line of sight"
            ),
            theme=theme,
            x_domain=(0.06, 0.17),
            y_domain=(-0.86, -0.34),
            x_ticks=[0.06, 0.08, 0.10, 0.12, 0.14, 0.16],
            y_ticks=[-0.8, -0.7, -0.6, -0.5, -0.4],
            x_label=r"横向坐标 $x_{24}$" if zh else r"$x_{24}$ position",
            y_label=r"纵向坐标 $y_{24}$" if zh else r"$y_{24}$ position",
            x_grid=True,
        )
        .add_legend("自举后验样本 (500)" if zh else "Bootstrap samples (500)", kind="dot", role="primary")
        .add_legend("真实目标位置" if zh else "True target position", kind="triangle", role="fg", fill_role="secondary")
        .add_scatter(sxs, sys_, r=2.6, role="primary", opacity=0.45)
        .add_markers([tx2[-1]], [ty2[-1]], glyph="triangle", size=16.0, role="fg", fill_role="secondary")
        .add_callout(
            tx2[-1],
            ty2[-1],
            f"真实目标位置 $({tx2[-1]:.3f}, {ty2[-1]:.3f})$" if zh else f"True target $({tx2[-1]:.3f}, {ty2[-1]:.3f})$",
            dx=12,
            dy=-8,
        )
        .render()
    )

    # Figs 8-11: 2D state component time series with 95% band
    def build_ts(
        title_zh: str,
        title_en: str,
        sub_zh: str,
        sub_en: str,
        mean_lbl_zh: str,
        mean_lbl_en: str,
        true_lbl_zh: str,
        true_lbl_en: str,
        y_domain: tuple[float, float],
        y_ticks: list[float],
        y_lbl_zh: str,
        y_lbl_en: str,
        mean_arr: list[float],
        lo_arr: list[float],
        hi_arr: list[float],
        true_arr: list[float],
        role: str,
        x_left: float | None = None,
    ) -> str:
        return (
            Chart(
                title_zh if zh else title_en,
                subtitle=sub_zh if zh else sub_en,
                theme=theme,
                x_domain=(1, 24),
                y_domain=y_domain,
                x_ticks=[1, 4, 8, 12, 16, 20, 24],
                y_ticks=y_ticks,
                x_label=r"时间步 $k$" if zh else r"Time step $k$",
                y_label=y_lbl_zh if zh else y_lbl_en,
                x_left=x_left,
            )
            .add_legend(mean_lbl_zh if zh else mean_lbl_en, kind="line", role=role)
            .add_legend("95% 概率区间" if zh else "95% probability interval", kind="band", role=role)
            .add_legend(true_lbl_zh if zh else true_lbl_en, kind="triangle", role="fg", fill_role="card")
            .add_band(k2, lo_arr, hi_arr, role=role, opacity=0.19)
            .add_line(k2, mean_arr, role=role)
            .add_markers(k2, true_arr, glyph="triangle", size=9.0, role="fg", fill_role="card")
            .render()
        )

    svgs["fig8"] = build_ts(
        "自举粒子滤波横向位置估计", r"Bootstrap Filter $x$-Position Estimate",
        r"$x_k$ 后验均值与 95% 概率区间 · 覆盖率 24/24", r"Posterior mean and 95% interval for $x_k$ · Coverage 24/24",
        "自举粒子滤波后验均值", "Bootstrap filter mean",
        r"真实位置 $x_k$", r"True $x_k$",
        (-0.12, 0.18), [-0.10, -0.05, 0.0, 0.05, 0.10, 0.15],
        r"横向位置 $x_k$", r"$x_k$ position",
        bx2, bx2_lo, bx2_hi, tx2, "primary",
    )
    svgs["fig9"] = build_ts(
        "自举粒子滤波横向速度估计", r"Bootstrap Filter $x$-Velocity Estimate",
        "横向速度后验均值与 95% 概率区间 · 覆盖率 24/24", r"Posterior mean and 95% interval for $x$-velocity · Coverage 24/24",
        "自举粒子滤波后验均值", "Bootstrap filter mean",
        "真实速度", r"True $x$-velocity",
        (-0.012, 0.018), [-0.010, -0.005, 0.0, 0.005, 0.010, 0.015],
        r"横向速度 $\dot{x}_k$", r"$x$-velocity $\dot{x}_k$",
        bvx2, bvx2_lo, bvx2_hi, tvx2, "primary", x_left=82.0,
    )
    svgs["fig10"] = build_ts(
        "一阶线性化滤波横向位置估计", r"EKF $x$-Position Estimate",
        r"$x_k$ 后验均值与 95% 概率区间 · 协方差过度收敛导致发散", r"Posterior mean and 95% interval for $x_k$ · Over-optimistic collapse & divergence",
        "一阶线性化后验均值", "EKF posterior mean",
        r"真实位置 $x_k$", r"True $x_k$",
        (-0.08, 0.34), [-0.05, 0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30],
        r"横向位置 $x_k$", r"$x_k$ position",
        ex2, ex2_lo, ex2_hi, tx2, "secondary",
    )
    svgs["fig11"] = build_ts(
        "一阶线性化滤波横向速度估计", r"EKF $x$-Velocity Estimate",
        "横向速度后验均值与 95% 概率区间 · 飞掠期出现剧烈尖峰", r"Posterior mean and 95% interval for $x$-velocity · Severe flypast spike",
        "一阶线性化后验均值", "EKF posterior mean",
        "真实速度", r"True $x$-velocity",
        (-0.02, 0.07), [-0.02, 0.0, 0.02, 0.04, 0.06],
        r"横向速度 $\dot{x}_k$", r"$x$-velocity $\dot{x}_k$",
        evx2, evx2_lo, evx2_hi, tvx2, "secondary", x_left=82.0,
    )

    if zh:
        for name, content in svgs.items():
            m = FORBIDDEN_ZH_PATTERN.search(content)
            if m:
                raise ValueError(f"Forbidden eponymous term '{m.group(0)}' found in figs_zh/{name}.svg")
    return svgs


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Gordon (1993) bilingual charts using htd_charts.")
    ap.add_argument("--sim", required=True, help="Path to sim_data.json")
    ap.add_argument("--out-dir", required=True, help="Output directory for figs_en/ and figs_zh/")
    ap.add_argument("--theme", default="editorial-academic", help="Chart theme name")
    ap.add_argument("--no-pdf", action="store_true", help="Skip headless Chrome PDF export")
    args = ap.parse_args()

    sim = json.loads(Path(args.sim).read_text(encoding="utf-8"))
    out_root = Path(args.out_dir)
    all_svgs: list[Path] = []
    for lang in ("en", "zh"):
        out_dir = out_root / f"figs_{lang}"
        out_dir.mkdir(parents=True, exist_ok=True)
        charts = build_all_charts(sim, lang, theme=args.theme)
        for i in range(1, 12):
            p = out_dir / f"fig{i}.svg"
            p.write_text(charts[f"fig{i}"], encoding="utf-8")
            all_svgs.append(p)
    if not args.no_pdf:
        export_pdfs_via_chrome(all_svgs, theme=args.theme)
    print(f"Rendered {len(all_svgs)} SVGs{' and PDFs' if not args.no_pdf else ''} into {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
