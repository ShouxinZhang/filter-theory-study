"""状态轨迹与观测分轴对照，冻结观测只用于事后展示。"""
from pathlib import Path
import matplotlib.pyplot as plt
from pipeline.common import digest_file
from plot_style import COLORS, LINESTYLES, save


def trajectory_figure(run_dir, output, rows, config, dataset, read_csv):
    trial = dataset["trials"][0]
    directory = Path(dataset["directory"])
    observation_path = directory / trial["observations"]
    if digest_file(observation_path) != trial["observations_sha256"]:
        raise RuntimeError("轨迹图观测文件哈希不匹配: " + str(observation_path))
    truth = read_csv(directory / trial["truth"])
    observations = read_csv(observation_path)
    steps = [int(row["step"]) for row in truth]
    if steps != [int(row["step"]) for row in observations]:
        raise RuntimeError("轨迹图真值与观测时间步不一致")
    state = [float(row["x"]) for row in truth]
    measured = [float(row["y"]) for row in observations]
    # 仅映射真值以展示观测空间参考线，不在 Python 中重新计算评估指标。
    model = config["dataset"]["model"]
    if model == "gordon":
        noiseless = [x * x / 20 for x in state]
        observation_label = r"无噪声观测 $h(x_k)=x_k^2/20$"
    elif model == "linear":
        noiseless = state
        observation_label = r"无噪声观测 $h(x_k)=x_k$"
    else:
        raise ValueError("轨迹图尚未定义此模型的观测映射: " + model)
    intervals = sorted({min(config["intervals"]), max(config["intervals"])})
    fig, axes = plt.subplots(2 * len(intervals), 1, figsize=(12, 5.4 * len(intervals)),
                             sharex=True, gridspec_kw={"height_ratios": [1.6, 1] * len(intervals)})
    for index, interval in enumerate(intervals):
        state_ax, obs_ax = axes[2 * index:2 * index + 2]
        active = [k % interval == 0 for k in steps]
        state_ax.plot(steps, state, color="black", lw=1.5, label=r"真实状态 $x_k$")
        for row in rows:
            if int(row["interval"]) != interval:
                continue
            path = run_dir / "jobs" / row["config_id"] / ("trial_%04d" % trial["trial"]) / "filter.csv"
            if not path.exists():
                continue
            data = read_csv(path)
            if ([int(r["step"]) for r in data] != steps or
                    [bool(int(r["observed"])) for r in data] != active):
                raise RuntimeError("轨迹图滤波输出的时间步或观测掩码不一致: " + str(path))
            algorithm = row["algorithm"]
            state_ax.plot(steps, [float(r["post_mean"]) for r in data],
                          color=COLORS[algorithm], linestyle=LINESTYLES[algorithm], label=algorithm.upper())
        state_ax.set(ylabel=r"状态 $x_k$", title=r"固定首条轨迹，观测间隔 $m=%s$" % interval)
        state_ax.legend(ncol=5, fontsize=8)
        obs_ax.plot(steps, noiseless, color="black", lw=1, label=observation_label)
        # 屏蔽点只供解释原始数据，实心点才是该帧率下算法实际收到的观测。
        for received, label, color, marker in (
                (False, r"屏蔽观测 $y_k$（未输入算法）", "#b0b0b0", "x"),
                (True, r"已用观测 $y_k$", "#9333ea", "o")):
            selected = [j for j, used in enumerate(active) if used == received]
            if selected:
                obs_ax.scatter([steps[j] for j in selected], [measured[j] for j in selected],
                               c=color, marker=marker, s=16, linewidths=0.8, label=label, zorder=3)
        obs_ax.set(ylabel=r"观测 $y_k$", xlabel=r"状态步 $k$")
        obs_ax.tick_params(axis="x", labelbottom=True)
        obs_ax.legend(ncol=3, fontsize=8)
    # 各帧率使用相同纵轴范围，便于对照相同轨迹；状态与观测仍分开定标。
    for group in (axes[::2], axes[1::2]):
        low = min(ax.get_ylim()[0] for ax in group)
        high = max(ax.get_ylim()[1] for ax in group)
        for ax in group:
            ax.set_ylim(low, high)
    save(fig, output, "trajectory.png")
