"""绘制 C++ 输出的逐时刻 RMSE，累计 RMSE 使用独立图避免概念混淆。"""
import math
import matplotlib.pyplot as plt
from plot_style import COLORS, LINESTYLES, save

def time_series_figures(output, rows, config):
    selected = {}
    for row in rows:
        algorithm = row["algorithm"]
        if algorithm not in ("kf", "ekf") and int(row["n"]) != config["reference_n"]:
            continue
        if algorithm == "etpf" and not math.isclose(float(row["epsilon"]), config["reference_epsilon"]):
            continue
        selected.setdefault((int(row["interval"]), algorithm), []).append(row)
    intervals = config["intervals"]
    ncols = min(2, len(intervals))
    nrows = math.ceil(len(intervals) / ncols)
    descriptions = [
        ("rmse", r"逐时刻跨轨迹 $\mathrm{RMSE}_k$", "rmse_time.png", False),
        ("rmse", r"逐时刻跨轨迹 $\mathrm{RMSE}_k$（对数纵轴）", "rmse_time_log.png", True),
        ("cumulative_rmse", r"截至当前时刻的累计 $\mathrm{RMSE}_{1:k}$", "rmse_cumulative.png", False),
    ]
    for field, title, name, logarithmic in descriptions:
        values = [float(r[field]) for points in selected.values() for r in points]
        ymax = max(values, default=1)
        ymin = min(values, default=1)
        fig, axs = plt.subplots(nrows, ncols, figsize=(7.2, 2.65 * nrows + 0.35),
                                sharex=True, sharey=True, squeeze=False)
        for ax, interval in zip(axs.flat, intervals):
            trials = set()
            for algorithm in config["algorithms"]:
                points = sorted(selected.get((interval, algorithm), []), key=lambda r: int(r["step"]))
                if not points:
                    continue
                trials.update(int(r["trials"]) for r in points)
                ax.plot([int(r["step"]) for r in points], [float(r[field]) for r in points],
                        color=COLORS[algorithm], linestyle=LINESTYLES[algorithm], label=algorithm.upper())
            ax.set(title=r"观测间隔 $m=%s$，相对帧率 $1/%s$" % (interval, interval),
                   xlabel=r"状态步 $k$", ylabel=(r"$\mathrm{RMSE}_k$" if field == "rmse" else r"$\mathrm{RMSE}_{1:k}$"))
            # 共享纵轴须使用全部子图的数据范围，避免先设置下界后冻结自动缩放
            if logarithmic and ymin > 0:
                ax.set_yscale("log")
                ax.set_ylim(ymin * 0.8, ymax * 1.1)
            elif logarithmic:
                ax.set_yscale("symlog", linthresh=0.01)
                ax.set_ylim(0, max(0.01, ymax * 1.1))
                ax.set_ylabel(r"$\mathrm{RMSE}_k$（零附近为线性刻度）")
            else:
                ax.set_ylim(0, max(1e-12, ymax * 1.05))
            if not trials:
                ax.text(0.5, 0.5, "无完成数据", transform=ax.transAxes, ha="center")
        for ax in list(axs.flat)[len(intervals):]:
            ax.set_visible(False)
        handles, labels = axs.flat[0].get_legend_handles_labels()
        fig.suptitle(r"%s，$N=%s$，$\mathrm{ETPF}$ $\varepsilon=%s$" % (title, config["reference_n"],
                     config["reference_epsilon"]), fontsize=11, y=1.01)
        fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.97),
                   ncol=len(handles), frameon=False)
        save(fig, output, name, rect=(0, 0, 1, 0.94 if nrows == 1 else 0.98))
