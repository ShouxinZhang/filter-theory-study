"""绘图：指标随观测步数的曲线、在线耗时对比、粒子还原图像示例。图中文字用英文缩写以避免字体问题。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch

STYLE = {  # 方法名 -> (图例, 颜色, 线型)
    "bpf": ("BPF (no transport)", "tab:gray", "--"),
    "bpf_jitter": ("BPF + jitter", "tab:brown", ":"),
    "etpf": ("ETPF", "tab:blue", "-"),
    "otpf": ("OTPF (per-step training)", "tab:orange", "-"),
    "amortized": ("A-OTPF (ours)", "tab:red", "-"),
}


def curves(results, path):
    """四联图：识别准确率、类别后验平方误差、还原误差、粒子离散程度。"""
    panels = [("acc", "recognition accuracy"), ("brier", "Brier score"),
              ("mse", "restoration MSE"), ("spread", "particle spread")]
    fig, axes = plt.subplots(1, 4, figsize=(16, 3.4))
    for ax, (key, title) in zip(axes, panels):
        for name, r in results.items():
            label, color, ls = STYLE[name]
            ax.plot(range(1, len(r[key]) + 1), r[key], ls, color=color, label=label, lw=1.8)
        ax.set_xlabel("observation step $k$")
        ax.set_title(title)
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=7.5)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def runtime(results, path):
    """每张图像每步的平均在线耗时（对数坐标）。"""
    names = list(results)
    vals = [sum(results[n]["time"]) / len(results[n]["time"]) * 1e3 for n in names]
    fig, ax = plt.subplots(figsize=(5, 3.2))
    ax.bar([STYLE[n][0].split(" (")[0] for n in names], vals, color=[STYLE[n][1] for n in names])
    ax.set_yscale("log")
    ax.set_ylabel("online time per image per step (ms)")
    ax.tick_params(axis="x", labelsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


@torch.no_grad()
def gallery(ctx, runners, z0, y_full, steps, path, n_show=6):
    """单张图像的示例：首行为累积观测，其余各行为各方法在选定时刻的若干粒子还原图像。"""
    fig, axes = plt.subplots(len(runners) + 1, len(steps) * n_show,
                             figsize=(len(steps) * n_show * 0.62, (len(runners) + 1) * 0.72))
    for ax in axes.flat:
        ax.axis("off")
    for j, k in enumerate(steps):
        obs = (y_full[0] * ctx.cum_masks[k - 1]).clamp(0, 1).view(28, 28).cpu()
        axes[0, j * n_show].imshow(obs, cmap="gray", vmin=0, vmax=1)
        axes[0, j * n_show].set_title(f"k={k}", fontsize=7)
    for i, (name, fn) in enumerate(runners.items(), start=1):
        gen = fn(ctx, z0, y_full)
        for k in range(1, max(steps) + 1):
            z, _ = next(gen)
            if k in steps:
                j = steps.index(k)
                imgs = ctx.model.restore(z[0, :n_show]).view(-1, 28, 28).cpu()
                for p in range(n_show):
                    axes[i, j * n_show + p].imshow(imgs[p], cmap="gray", vmin=0, vmax=1)
        axes[i, 0].text(-0.3, 0.5, STYLE[name][0].split(" (")[0], transform=axes[i, 0].transAxes,
                        fontsize=7, ha="right", va="center")
    fig.subplots_adjust(wspace=0.04, hspace=0.04, left=0.09)
    fig.savefig(path, dpi=220)
    plt.close(fig)
