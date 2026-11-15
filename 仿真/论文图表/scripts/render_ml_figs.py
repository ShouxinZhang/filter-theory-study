import csv
import json
import sys
from dataclasses import replace
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.text import Text
import numpy as np
import torch

simsun_path = Path("/usr/local/share/fonts/simsun.ttc")
if simsun_path.exists():
    font_manager.fontManager.addfont(str(simsun_path))
    chinese_family = font_manager.FontProperties(fname=str(simsun_path)).get_name()
else:
    chinese_family = "Noto Serif CJK SC"

western_families = []
for fp in [
    "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Italic.ttf",
]:
    if Path(fp).exists():
        font_manager.fontManager.addfont(fp)
        western_families.append(font_manager.FontProperties(fname=fp).get_name())
western_families.append("STIXGeneral")
seen = set()
font_stack = []
for f in western_families + [chinese_family]:
    if f not in seen:
        seen.add(f)
        font_stack.append(f)

plt.rcParams.update({
    "font.family": font_stack,
    "mathtext.fontset": "stix",
    "font.size": 9.8,
    "axes.titlesize": 10.2,
    "axes.labelsize": 9.8,
    "xtick.labelsize": 9.2,
    "ytick.labelsize": 9.2,
    "legend.fontsize": 9.2,
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

def fix_mixed_math_cjk(fig):
    for artist in fig.findobj(match=Text):
        label = artist.get_text()
        if "$" in label and any("\u3000" <= ch <= "\u9fff" or "\uff00" <= ch <= "\uffef" for ch in label):
            artist.set_fontfamily(chinese_family)

REPO = Path(__file__).resolve().parents[3]                   # 仓库根目录
TASK = REPO / "仿真/数字识别"                                  # 数字识别实验目录，须先运行其 run.py
OUT_FIG = REPO / "仿真/论文图表/figures"                       # 生成后拷入论文的 figs/completed_work/
OUT_FIG.mkdir(parents=True, exist_ok=True)

# 0. Refresh logistic_robustness.pdf with >=9pt font & italic $k$, $D_k$
LOG_DATA = REPO / "仿真/论文图表/data/logistic"
if (LOG_DATA / "curves.csv").exists():
    with (LOG_DATA / "curves.csv").open() as f:
        rows = list(csv.DictReader(f))
    def series(algorithm, metric):
        selected = sorted(
            (r for r in rows if r["algorithm"] == algorithm and r["metric"] == metric),
            key=lambda r: int(r["step"]),
        )
        return np.array([float(r["estimate"]) for r in selected])

    fig, axes = plt.subplots(1, 2, figsize=(5.5, 2.25))
    steps_log = np.arange(1, 1001)
    for algorithm, color, linestyle in (("bpf", "#0284c7", "--"), ("etpf", "#0d9488", "-")):
        mse = series(algorithm, "post_state_mse")
        axes[0].plot(
            steps_log.reshape(-1, 20).mean(axis=1),
            mse.reshape(-1, 20).mean(axis=1),
            color=color,
            linestyle=linestyle,
            lw=1.35,
            label=algorithm.upper(),
        )
        axes[1].plot(steps_log, series(algorithm, "unique_particles"), color=color, linestyle=linestyle, lw=1.35)
    axes[0].plot(
        steps_log.reshape(-1, 20).mean(axis=1),
        series("bpf", "bayes_risk").reshape(-1, 20).mean(axis=1),
        color="#475569",
        linestyle=":",
        lw=1.35,
        label="Bayes",
    )
    axes[0].set(title="(a) 均方误差", xlabel="状态步 $k$", ylabel="MSE", xlim=(0, 1000), ylim=(0, 0.30))
    axes[1].set(
        title="(b) 不同粒子位置数",
        xlabel="状态步 $k$",
        ylabel="平均 $D_k$",
        xscale="log",
        xlim=(1, 1000),
        ylim=(0, 132),
    )
    axes[1].set_yticks([1, 32, 64, 96, 128])
    axes[1].set_xticks([1, 10, 100, 1000], labels=["1", "10", "100", "1000"])
    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, alpha=0.18, linewidth=0.5)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fix_mixed_math_cjk(fig)
    fig.tight_layout(rect=(0, 0.13, 1, 1), w_pad=1.3)
    fig.savefig(OUT_FIG / "logistic_robustness.pdf", bbox_inches="tight")
    plt.close(fig)
    print("Saved logistic_robustness.pdf")

main_d = json.load(open(TASK / "outputs/metrics/main.json"))
extra_d = json.load(open(TASK / "outputs/metrics/extra.json"))
all_seeds = [main_d["results"], extra_d["seeds"]["1"], extra_d["seeds"]["2"]]

STYLE = [
    ("bpf", "BPF", "#1f77b4", "--"),
    ("bpf_jitter", "BPF 加扰动", "#8c564b", ":"),
    ("etpf", "ETPF", "#008060", "-."),
    ("otpf", "OTPF", "#e67e22", "-"),
    ("amortized", "摊销 OTPF", "#c0392b", "-"),
]

# 1. Render ml_curves.pdf at native thesis width (~5.85 in -> >= 9 pt rendered text!)
panels = [
    ("acc", "(a) 识别准确率", "准确率"),
    ("brier", "(b) 类别后验平方误差", "平方误差"),
    ("mse", "(c) 还原均方误差", "MSE"),
    ("spread", "(d) 潜空间粒子离散度", "离散度"),
]

fig, axes = plt.subplots(2, 2, figsize=(5.85, 4.4))
steps = np.arange(1, 17)

for ax, (key, title, ylabel) in zip(axes.flat, panels):
    for m_key, label, color, ls in STYLE:
        arr = np.array([s[m_key][key] for s in all_seeds], dtype=float)
        mean = arr.mean(axis=0)
        std = arr.std(axis=0, ddof=1)
        ax.plot(steps, mean, linestyle=ls, color=color, lw=1.5, label=label)
        ax.fill_between(steps, mean - std, mean + std, color=color, alpha=0.12, linewidth=0)
    if key == "acc":
        ax.axhline(main_d["info"]["ceiling_acc"], color="#555555", ls=(0, (3, 3)), lw=1.0, label="全图直接压缩上限")
    ax.set_title(title, pad=5)
    ax.set_xlabel("观测步 $k$", labelpad=2)
    ax.set_ylabel(ylabel, labelpad=3)
    ax.set_xticks([1, 4, 8, 12, 16])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.85)
    ax.spines["bottom"].set_linewidth(0.85)
    ax.tick_params(length=3.0, width=0.8, pad=2)
    ax.grid(True, alpha=0.25, linewidth=0.5)

handles, labels = axes[0, 0].get_legend_handles_labels()
fig.legend(
    handles,
    labels,
    loc="lower center",
    ncol=3,
    frameon=False,
    bbox_to_anchor=(0.5, -0.005),
    handlelength=2.0,
    columnspacing=1.4,
    labelspacing=0.3,
)
fix_mixed_math_cjk(fig)
fig.tight_layout(rect=[0.0, 0.10, 1.0, 1.0], pad=0.35, w_pad=0.95, h_pad=0.85)
fig.savefig(OUT_FIG / "ml_curves.pdf")
plt.close(fig)
print("Saved ml_curves.pdf")

# 2. Render ml_gallery.pdf at native thesis width (~5.95 in -> >= 9 pt rendered text!)
sys.path.insert(0, str(TASK))
from latent_filter import data
from latent_filter.config import Config
from latent_filter.evaluate import Context, make_inputs
from latent_filter.filters import amortized, bpf, etpf, otpf_online
from latent_filter.observe import window_masks

cfg = Config()
ds = data.load(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
ck = TASK / "outputs/checkpoints"
model = torch.load(ck / "compress_restore_nd16.pt", weights_only=False)
readout = torch.load(ck / "readout_nd16.pt", weights_only=False)
t_net = torch.load(ck / "amortized_nd16.pt", weights_only=False)
masks, cum = window_masks(cfg.window, ds[0].device)
ctx = Context(cfg, model, readout, masks, cum, t_net)

with torch.no_grad():
    z_tr = model.compress(ds[0])

pick = 18
x1 = ds[2][pick:pick + 1]
z0, y1 = make_inputs(replace(cfg, n_particles=cfg.n_particles), z_tr, x1, cfg.seed)

show_runners = [
    ("BPF", bpf.run),
    ("ETPF", etpf.run),
    ("OTPF", otpf_online.run),
    ("摊销 OTPF", amortized.run),
]
show_steps = [6, 10, 16]
n_show = 6

obs_imgs = {}
for k in show_steps:
    obs_imgs[k] = (y1[0] * ctx.cum_masks[k - 1]).clamp(0, 1).view(28, 28).detach().cpu().numpy()

restored = {label: {} for label, _ in show_runners}
for label, fn in show_runners:
    gen = fn(ctx, z0, y1)
    for k in range(1, max(show_steps) + 1):
        z_cur, _ = next(gen)
        if k in show_steps:
            with torch.no_grad():
                imgs = ctx.model.restore(z_cur[0, :n_show]).clamp(0, 1).view(-1, 28, 28).cpu().numpy()
            restored[label][k] = imgs
    gen.close()

n_cols = len(show_steps) * n_show + (len(show_steps) - 1)
n_rows = len(show_runners) + 1
width_ratios = []
for j in range(len(show_steps)):
    width_ratios.extend([1.0] * n_show)
    if j < len(show_steps) - 1:
        width_ratios.append(0.35)

fig, axes = plt.subplots(
    n_rows,
    n_cols,
    figsize=(5.95, 2.15),
    gridspec_kw={"width_ratios": width_ratios, "wspace": 0.05, "hspace": 0.08},
)
for ax in axes.flat:
    ax.axis("off")

def col_offset(j):
    return j * (n_show + 1)

for j, k in enumerate(show_steps):
    c0 = col_offset(j)
    axes[0, c0].imshow(obs_imgs[k], cmap="gray", vmin=0, vmax=1, interpolation="nearest")
    axes[0, c0 + 2].text(
        1.05,
        1.14,
        f"观测步 $k = {k}$",
        transform=axes[0, c0 + 2].transAxes,
        fontsize=9.5,
        ha="center",
        va="bottom",
    )

axes[0, 0].text(
    -0.25,
    0.5,
    "累积观测",
    transform=axes[0, 0].transAxes,
    fontsize=9.5,
    ha="right",
    va="center",
)

for r_idx, (label, _) in enumerate(show_runners, start=1):
    axes[r_idx, 0].text(
        -0.25,
        0.5,
        label,
        transform=axes[r_idx, 0].transAxes,
        fontsize=9.5,
        ha="right",
        va="center",
    )
    for j, k in enumerate(show_steps):
        c0 = col_offset(j)
        for p in range(n_show):
            axes[r_idx, c0 + p].imshow(
                restored[label][k][p], cmap="gray", vmin=0, vmax=1, interpolation="nearest"
            )

fix_mixed_math_cjk(fig)
fig.subplots_adjust(left=0.145, right=0.995, top=0.85, bottom=0.02)
fig.savefig(OUT_FIG / "ml_gallery.pdf")
plt.close(fig)
print("Saved ml_gallery.pdf")
