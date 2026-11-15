"""只绘制 C++ 已计算的误差和置信区间，不重新计算滤波评估指标。"""
import csv
import math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from plot_style import COLORS, style, save
from plot_timeseries import time_series_figures
from plot_trajectory import trajectory_figure

def read_csv(path):
    with Path(path).open() as f:
        return list(csv.DictReader(f))

def figures(run_dir, rows, config, dataset):
    font_metadata = style()
    output = run_dir / "figures"
    output.mkdir(exist_ok=True)
    algorithms = config["algorithms"]
    intervals = config["intervals"]
    ref_n, ref_e = config["reference_n"], config["reference_epsilon"]

    def chosen(row):
        return (row["algorithm"] in ("kf", "ekf") or int(row["n"]) == ref_n) and (
            row["algorithm"] != "etpf" or math.isclose(float(row["epsilon"]), ref_e))

    fig, ax = plt.subplots(figsize=(8, 4.6))
    for alg in algorithms:
        points = sorted([r for r in rows if r["algorithm"] == alg and chosen(r)], key=lambda r: int(r["interval"]))
        if not points:
            continue
        x = [1 / int(r["interval"]) for r in points]
        y = [float(r["rmse"]) for r in points]
        low = [float(r["ci_low"]) for r in points]
        high = [float(r["ci_high"]) for r in points]
        ax.plot(x, y, "o-", label=alg.upper(), color=COLORS[alg])
        ax.fill_between(x, low, high, color=COLORS[alg], alpha=0.12)
    ax.set_xscale("log", base=2)
    ax.set_xticks([1 / m for m in intervals], [str(1 / m) for m in intervals])
    ax.set(xlabel=r"相对观测帧率 $1/m$", ylabel=r"全时域 $\mathrm{RMSE}$",
           title=r"帧率消融，固定 $N=%s$，$\mathrm{ETPF}$ $\varepsilon=%s$" % (ref_n, ref_e))
    ax.legend(ncol=4)
    save(fig, output, "rmse_rate.png")

    fig, axs = plt.subplots(1, len(intervals), figsize=(4 * len(intervals), 4), squeeze=False)
    for ax, m in zip(axs[0], intervals):
        for alg in algorithms:
            points = sorted([r for r in rows if r["algorithm"] == alg and int(r["interval"]) == m
                and (alg != "etpf" or math.isclose(float(r["epsilon"]), ref_e))], key=lambda r: int(r["n"]))
            if not points:
                continue
            if alg in ("kf", "ekf"):
                ax.axhline(float(points[0]["rmse"]), color=COLORS[alg], linestyle="--", label=alg.upper())
            else:
                ax.plot([int(r["n"]) for r in points], [float(r["rmse"]) for r in points],
                        "o-", color=COLORS[alg], label=alg.upper())
        ax.set(title="每 %s 步观测" % m, xlabel=r"粒子 / 集合数 $N$", ylabel=r"$\mathrm{RMSE}$")
    axs[0, 0].legend()
    save(fig, output, "rmse_particles.png")

    fig, axs = plt.subplots(1, len(config["particles"]), figsize=(4.2 * len(config["particles"]), 4), squeeze=False)
    lookup = {(int(r["n"]), float(r["epsilon"]), int(r["interval"])): r for r in rows if r["algorithm"] == "etpf"}
    # 全部 N 共用色标，避免颜色相同却代表不同误差
    values = [float(r["rmse"]) for r in lookup.values()]
    vmin, vmax = (min(values), max(values)) if values else (0, 1)
    for ax, n in zip(axs[0], config["particles"]):
        data = np.array([[float(lookup.get((n, e, m), {}).get("rmse", "nan"))
                          for m in intervals] for e in config["epsilons"]])
        image = ax.imshow(data, aspect="auto", cmap="viridis", vmin=vmin, vmax=vmax)
        ax.grid(False)
        ax.set_xticks(range(len(intervals)), intervals)
        ax.set_yticks(range(len(config["epsilons"])), config["epsilons"])
        ax.set(xlabel=r"观测间隔 $m$", ylabel=r"$\varepsilon$", title=r"$\mathrm{ETPF}$，$N=%s$" % n)
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                color = "black" if data[i, j] > vmin + 0.6 * (vmax - vmin) else "white"
                ax.text(j, i, "%.2f" % data[i, j], ha="center", va="center", color=color, fontsize=9)
        fig.colorbar(image, ax=ax, label=r"$\mathrm{RMSE}$")
    save(fig, output, "epsilon_rate.png")

    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    for alg in algorithms:
        points = [r for r in rows if r["algorithm"] == alg and chosen(r)]
        if not points:
            continue
        axs[0].plot([1 / int(r["interval"]) for r in points],
                    [float(r["update_us_per_observation"]) for r in points], "o-", label=alg.upper(), color=COLORS[alg])
    axs[0].set(yscale="log", xlabel=r"相对观测帧率 $1/m$", ylabel=r"每次更新耗时 / $\mathrm{\mu s}$", title="更新耗时（并发模式见报告）")
    axs[0].legend()
    for n in config["particles"]:
        p = sorted([r for r in rows if r["algorithm"] == "etpf" and int(r["n"]) == n
                    and int(r["interval"]) == min(intervals)], key=lambda r: float(r["epsilon"]))
        axs[1].plot([float(r["epsilon"]) for r in p],
                    [float(r["ot_nonconverged_fraction"]) for r in p], "o-", label=r"$N=%s$" % n)
    axs[1].set(xscale="log", xlabel=r"$\varepsilon$", ylabel="未达到容差的更新比例", ylim=(-0.03, 1.03), title="最高帧率下的求解诊断")
    axs[1].legend()
    save(fig, output, "runtime_convergence.png")

    trajectory_figure(run_dir, output, [row for row in rows if chosen(row)], config, dataset, read_csv)
    time_series_figures(output, read_csv(run_dir / "time_series.csv"), config)
    return font_metadata
