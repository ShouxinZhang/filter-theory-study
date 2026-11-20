#!/usr/bin/env python3
"""Julier & Uhlmann (1997) Chinese chart builder example using htd_charts.

All mathematical expressions use explicit $...$ delimiters pre-rendered via
MathJax SVG paths; zero CSS, HTML, or SVG glyph path hardcoding.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

CHARTS_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(CHARTS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CHARTS_SCRIPTS))

from htd_charts import Chart, export_pdfs_via_chrome  # noqa: E402

FORBIDDEN_ZH_PATTERN = re.compile(
    r"(EKF|UKF|Kalman|Bayesian|Gaussian|Cholesky|Taylor|Jacobian|Julier|Uhlmann|卡尔曼|高斯|贝叶斯|乔里斯基|泰勒|雅可比)",
    re.IGNORECASE,
)


def build_all_charts(sim: dict[str, Any], theme: str = "editorial-academic") -> dict[str, str]:
    polar = sim["polar"]
    reentry = sim["reentry"]
    svgs: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Fig 1: Polar-to-Cartesian Transformation & 1-sigma Error Ellipses
    # ------------------------------------------------------------------
    cloud = polar["cloud_xy"]
    cxs = [float(p[0]) for p in cloud]
    cys = [float(p[1]) for p in cloud]
    t_el = polar["true_ellipse"]
    l_el = polar["lin_ellipse"]
    u_el = polar["ut_ellipse"]
    tm = polar["true_mean"]
    lm = polar["lin_mean"]
    um = polar["ut_mean"]
    sig_pts = polar["ut_sigma_xy"]

    svgs["fig1"] = (
        Chart(
            r"极坐标到直角坐标变换：均值与 $1\sigma$ 误差椭圆对比",
            subtitle=r"$r \sim \mathcal{N}(1, 0.02^2)$，方位角标准差 $15^\circ$ · 无迹变换精准捕捉弯折均值与纵向展宽",
            theme=theme,
            x_domain=(-0.75, 0.75),
            y_domain=(0.72, 1.10),
            x_ticks=[-0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6],
            y_ticks=[0.75, 0.85, 0.95, 1.05],
            x_label=r"横向坐标 $x$",
            y_label=r"纵向坐标 $y$",
            x_grid=True,
        )
        .add_legend("真实样本云 (600)", kind="dot", role="accent")
        .add_legend(r"真实均值与 $1\sigma$ 椭圆", kind="line", role="fg")
        .add_legend(r"无迹变换 ($\kappa = 1$)", kind="line", role="primary")
        .add_legend("一阶线性化近似", kind="line", role="secondary", dashed=True)
        .add_scatter(cxs, cys, r=2.2, role="accent", opacity=0.28)
        .add_line(t_el["x"], t_el["y"], role="fg", thin=True)
        .add_line(l_el["x"], l_el["y"], role="secondary", dashed=True)
        .add_line(u_el["x"], u_el["y"], role="primary")
        .add_markers([p[0] for p in sig_pts], [p[1] for p in sig_pts], glyph="triangle", size=8.5, role="primary", fill_role="card")
        .add_markers([tm[0]], [tm[1]], glyph="star", size=11.0, role="fg")
        .add_markers([lm[0]], [lm[1]], glyph="triangle", size=10.5, role="secondary", fill_role="secondary")
        .add_callout(lm[0], lm[1], f"线性化偏高均值 (${lm[1]:.3f}$)", dx=16, dy=-10)
        .add_callout(um[0], um[1], f"真实与无迹均值 (${um[1]:.4f}$)", dx=16, dy=18)
        .render()
    )

    # ------------------------------------------------------------------
    # Fig 2: Kappa Sensitivity Sweep (Mean & Covariance Error)
    # ------------------------------------------------------------------
    ks = polar["kappa_sweep"]
    kappas = [float(v) for v in ks["kappa"]]
    cov_errs = [float(v) * 1e3 for v in ks["ut_cov_err"]]
    lin_cov_e = float(ks["lin_cov_err"]) * 1e3
    idx_k1 = kappas.index(1.0)

    svgs["fig2"] = (
        Chart(
            r"缩放参数 $\kappa$ 对无迹变换协方差逼近误差的影响",
            subtitle=r"二维极坐标变换 ($n = 2$) · 取 $\kappa = 1$ ($n + \kappa = 3$) 时匹配正态分布四阶矩，误差达极小值",
            theme=theme,
            x_domain=(-1.2, 4.0),
            y_domain=(0.0, 5.8),
            x_ticks=[-1.0, 0.0, 1.0, 2.0, 3.0, 4.0],
            y_ticks=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
            x_label=r"缩放参数 $\kappa$",
            y_label=r"协方差范数误差 ($\times 10^{-3}$)",
        )
        .add_legend("无迹变换协方差误差", kind="line", role="primary")
        .add_legend("一阶线性化误差基线", kind="line", role="secondary", dashed=True)
        .add_legend(r"四阶矩最优点 $\kappa = 1$", kind="ref", role="fg")
        .add_line([kappas[0], kappas[-1]], [lin_cov_e, lin_cov_e], role="secondary", dashed=True)
        .add_line(kappas, cov_errs, role="primary")
        .add_vline(1.0, marker_glyph="star", marker_size=10.5, marker_role="fg")
        .add_top_label(1.0, r"$\kappa = 1$ ($n + \kappa = 3$)", dx=10, dy=20, anchor="start")
        .add_callout(1.0, cov_errs[idx_k1], f"极小误差 ${cov_errs[idx_k1]:.2f} \\times 10^{{-3}}$", dx=14, dy=-22, leader_role="primary", leader_dx=10, leader_dy=-18)
        .add_callout(2.8, lin_cov_e, f"一阶线性化 (${lin_cov_e:.2f} \\times 10^{{-3}}$)", dx=0, dy=-12, anchor="middle")
        .render()
    )

    # ------------------------------------------------------------------
    # Fig 3: Reentry Vehicle Trajectory & Radar Geometry
    # ------------------------------------------------------------------
    traj = reentry["traj_true_xy"]
    tx = [float(p[0]) for p in traj]
    ty = [float(p[1]) for p in traj]
    rx, ry = float(reentry["radar_xy"][0]), float(reentry["radar_xy"][1])
    R0 = float(reentry["earth_radius"])
    arc_ang = [math.radians(-6.5 + 0.2 * i) for i in range(66)]
    arc_x = [R0 * math.cos(a) for a in arc_ang]
    arc_y = [R0 * math.sin(a) for a in arc_ang]

    svgs["fig3"] = (
        Chart(
            "高超声速再入飞行器二维地心轨迹与雷达观测几何",
            subtitle=r"地球半径 $R_0 = 6374\,\mathrm{km}$ · 地面雷达位于 $(6374, 0)\,\mathrm{km}$ · 追踪时长 $160\,\mathrm{s}$",
            theme=theme,
            x_domain=(6320.0, 6520.0),
            y_domain=(-460.0, 400.0),
            x_ticks=[6320, 6360, 6400, 6440, 6480, 6520],
            y_ticks=[-400, -200, 0, 200, 400],
            x_label=r"地心横向坐标 $x_1\,(\mathrm{km})$",
            y_label=r"地心纵向坐标 $x_2\,(\mathrm{km})$",
            x_grid=True,
            x_left=82.0,
        )
        .add_legend("再入飞行器真实轨迹", kind="line", role="primary")
        .add_legend("地球表面弧线", kind="line", role="accent", dashed=True)
        .add_legend("地面追踪雷达", kind="observer", role="fg")
        .add_line(arc_x, arc_y, role="accent", dashed=True, thin=True)
        .add_line(tx, ty, role="primary")
        .add_markers([tx[0], tx[-1]], [ty[0], ty[-1]], glyph="star", size=10.0, role="fg")
        .add_markers([rx], [ry], glyph="observer", size=14.0, role="fg")
        .add_callout(rx, ry, r"地面雷达 $(6374, 0)$", dx=14, dy=4)
        .add_callout(tx[0], ty[0], r"初始入轨 ($t = 0\,\mathrm{s}$)", dx=-12, dy=4, anchor="end")
        .add_callout(tx[-1], ty[-1], r"再入末段 ($t = 160\,\mathrm{s}$)", dx=-12, dy=-8, anchor="end")
        .render()
    )

    # ------------------------------------------------------------------
    # Fig 4: Reentry Position RMS Error Comparison
    # ------------------------------------------------------------------
    t_arr = [float(v) for v in reentry["t"]]
    ep = [float(v) for v in reentry["ekf_pos_rms"]]
    up = [float(v) for v in reentry["ukf_pos_rms"]]
    peak_idx = max(range(len(ep)), key=lambda i: ep[i] - up[i])

    svgs["fig4"] = (
        Chart(
            "再入算例位置估计均方根误差对比",
            subtitle="20 次独立仿真统计 · 强气动减速段无迹滤波显著压低线性化瞬态误差",
            theme=theme,
            x_domain=(0.0, 160.0),
            y_domain=(0.0, 1.85),
            x_ticks=[0, 20, 40, 60, 80, 100, 120, 140, 160],
            y_ticks=[0.0, 0.4, 0.8, 1.2, 1.6],
            x_label=r"追踪时间 $t\,(\mathrm{s})$",
            y_label=r"位置均方根误差 ($\mathrm{km}$)",
        )
        .add_legend(r"无迹滤波 ($\kappa = 0$)", kind="line", role="primary")
        .add_legend("一阶线性化滤波", kind="line", role="secondary", dashed=True)
        .add_line(t_arr, ep, role="secondary", dashed=True)
        .add_line(t_arr, up, role="primary")
        .add_callout(
            t_arr[peak_idx],
            ep[peak_idx],
            f"强减速段峰值差 ($t = {t_arr[peak_idx]:.0f}\\,\\mathrm{{s}}$)",
            dx=18,
            dy=-12,
            leader_role="secondary",
            leader_dx=14,
            leader_dy=-10,
        )
        .render()
    )

    # ------------------------------------------------------------------
    # Fig 5: Reentry Velocity RMS Error Comparison
    # ------------------------------------------------------------------
    ev = [float(v) for v in reentry["ekf_vel_rms"]]
    uv = [float(v) for v in reentry["ukf_vel_rms"]]

    svgs["fig5"] = (
        Chart(
            "再入算例速度估计均方根误差对比",
            subtitle=r"20 次独立仿真统计 · 随气动阻力段推进，速度误差收敛至 $0.01\,\mathrm{km/s}$ 量级",
            theme=theme,
            x_domain=(0.0, 160.0),
            y_domain=(0.0, 0.09),
            x_ticks=[0, 20, 40, 60, 80, 100, 120, 140, 160],
            y_ticks=[0.0, 0.02, 0.04, 0.06, 0.08],
            x_label=r"追踪时间 $t\,(\mathrm{s})$",
            y_label=r"速度均方根误差 ($\mathrm{km/s}$)",
            x_left=82.0,
        )
        .add_legend(r"无迹滤波 ($\kappa = 0$)", kind="line", role="primary")
        .add_legend("一阶线性化滤波", kind="line", role="secondary", dashed=True)
        .add_line(t_arr, ev, role="secondary", dashed=True)
        .add_line(t_arr, uv, role="primary")
        .render()
    )

    # ------------------------------------------------------------------
    # Fig 6: Ballistic Parameter x_5 Convergence (t = 0..80 s zoom)
    # ------------------------------------------------------------------
    rx5 = reentry["rep_x5"]
    n_zoom = sum(1 for tv in t_arr if tv <= 80.0)
    tz = t_arr[:n_zoom]
    x5_true = [float(v) for v in rx5["true"][:n_zoom]]
    x5_ekf = [float(v) for v in rx5["ekf"][:n_zoom]]
    x5_ukf = [float(v) for v in rx5["ukf"][:n_zoom]]
    x5_ulo = [float(v) for v in rx5["ukf_lo95"][:n_zoom]]
    x5_uhi = [float(v) for v in rx5["ukf_hi95"][:n_zoom]]
    ekf_pk_i = max(range(n_zoom), key=lambda i: x5_ekf[i])

    svgs["fig6"] = (
        Chart(
            r"未知气动弹道参数 $x_5$ 收敛过程与 95% 概率区间",
            subtitle=r"真实值 $x_5 = 0.6932$ · 强非线性入轨段一阶线性化出现明显超调，无迹滤波平稳锁定",
            theme=theme,
            x_domain=(0.0, 80.0),
            y_domain=(-0.2, 1.65),
            x_ticks=[0, 10, 20, 30, 40, 50, 60, 70, 80],
            y_ticks=[-0.2, 0.0, 0.4, 0.8, 1.2, 1.6],
            x_label=r"追踪时间 $t\,(\mathrm{s})$",
            y_label=r"气动弹道参数 $x_5$",
        )
        .add_legend("无迹滤波均值", kind="line", role="primary")
        .add_legend("无迹滤波 95% 概率区间", kind="band", role="primary")
        .add_legend("一阶线性化均值", kind="line", role="secondary", dashed=True)
        .add_legend("真实参数值", kind="line", role="fg")
        .add_band(tz, x5_ulo, x5_uhi, role="primary", opacity=0.18)
        .add_line(tz, x5_true, role="fg", thin=True)
        .add_line(tz, x5_ekf, role="secondary", dashed=True)
        .add_line(tz, x5_ukf, role="primary")
        .add_callout(
            tz[ekf_pk_i],
            x5_ekf[ekf_pk_i],
            f"线性化超调 (${x5_ekf[ekf_pk_i]:.2f}$)",
            dx=20,
            dy=4,
            leader_role="secondary",
            leader_dx=16,
            leader_dy=2,
        )
        .add_callout(60.0, x5_true[-1], r"真实值 ($0.693$)", dx=0, dy=-14, anchor="middle")
        .render()
    )

    for name, content in svgs.items():
        m = FORBIDDEN_ZH_PATTERN.search(content)
        if m:
            raise ValueError(f"Forbidden eponymous term '{m.group(0)}' found in {name}.svg")
    return svgs


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Julier & Uhlmann (1997) Chinese charts via htd_charts.")
    ap.add_argument("--sim", required=True, help="Path to sim_data.json")
    ap.add_argument("--out-dir", required=True, help="Output directory for fig1..fig6 SVG and PDF files")
    ap.add_argument("--theme", default="editorial-academic", help="Theme pack name")
    ap.add_argument("--no-pdf", action="store_true", help="Skip headless Chrome PDF export")
    args = ap.parse_args()

    sim = json.loads(Path(args.sim).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    charts = build_all_charts(sim, theme=args.theme)
    all_svgs: list[Path] = []
    for i in range(1, 7):
        p = out_dir / f"fig{i}.svg"
        p.write_text(charts[f"fig{i}"], encoding="utf-8")
        all_svgs.append(p)
    if not args.no_pdf:
        export_pdfs_via_chrome(all_svgs, theme=args.theme)
    print(f"Rendered {len(all_svgs)} SVGs{' and PDFs' if not args.no_pdf else ''} into {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
