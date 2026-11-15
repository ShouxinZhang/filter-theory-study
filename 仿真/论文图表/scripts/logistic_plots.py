"""Plot existing Q=0 results; no new filter runs or random draws."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"data/logistic"
OUT = ROOT/"figures"


def read(name):
    with (DATA / name).open() as f:
        return list(csv.DictReader(f))


def main():
    chinese_font = Path("/usr/local/share/fonts/simsun.ttc")
    if chinese_font.exists():
        font_manager.fontManager.addfont(str(chinese_font))
        chinese_family = font_manager.FontProperties(fname=str(chinese_font)).get_name()
    else:
        chinese_family = "Noto Serif CJK SC"
    plt.rcParams.update({
        "font.family": ["STIXGeneral", chinese_family], "mathtext.fontset": "stix",
        "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
        "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.unicode_minus": False, "axes.grid": True, "grid.alpha": .16,
        "lines.linewidth": 1.15, "pdf.fonttype": 42, "savefig.dpi": 180,
    })
    rows = read("curves.csv")
    def series(algorithm, metric):
        selected = sorted((r for r in rows if r["algorithm"] == algorithm
                           and r["metric"] == metric), key=lambda r: int(r["step"]))
        assert [int(r["step"]) for r in selected] == list(range(1, 1001))
        return np.array([float(r["estimate"]) for r in selected])

    summary = {(r["algorithm"], r["metric"]): float(r["estimate"])
               for r in read("summary.csv") if r["stage"] == "all"}
    fig, axes = plt.subplots(1, 2, figsize=(5.5, 2.12))
    steps = np.arange(1, 1001)
    for algorithm, color, linestyle in (("bpf", "#0284c7", "--"),
                                         ("etpf", "#0d9488", "-")):
        mse = series(algorithm, "post_state_mse")
        assert abs(mse.mean() - summary[algorithm, "post_state_mse"]) < 1e-12
        axes[0].plot(steps.reshape(-1, 20).mean(axis=1),
                     mse.reshape(-1, 20).mean(axis=1), color=color,
                     linestyle=linestyle, label=algorithm.upper())
        axes[1].plot(steps, series(algorithm, "unique_particles"),
                     color=color, linestyle=linestyle)
    axes[0].plot(steps.reshape(-1, 20).mean(axis=1),
                 series("bpf", "bayes_risk").reshape(-1, 20).mean(axis=1),
                 color="#475569", linestyle=":", label="Bayes")
    axes[0].set(title="(a) 均方误差", xlabel="状态步 k", ylabel="MSE",
                xlim=(0, 1000), ylim=(0, .30))
    axes[1].set(title="(b) 不同粒子位置数", xlabel="状态步 k", ylabel="平均 D",
                xscale="log", xlim=(1, 1000), ylim=(0, 132))
    axes[1].set_yticks([1, 32, 64, 96, 128])
    axes[1].set_xticks([1, 10, 100, 1000], labels=["1", "10", "100", "1000"])
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(.5, -.005))
    fig.tight_layout(rect=(0, .13, 1, 1), w_pad=1.5)
    OUT.mkdir(parents=True, exist_ok=True)
    for extension in ("pdf", "png"):
        fig.savefig(OUT / f"logistic_robustness.{extension}", bbox_inches="tight")
    plt.close(fig)

    metrics = [("不可约 Bayes 误差", "bayes_risk"),
               ("算法偏差平方", "bias_squared_corrected"),
               ("算法随机波动", "algorithm_fluctuation"),
               ("当前重采样扰动", "resampling_disturbance"),
               ("实测总 MSE", "post_state_mse")]
    lines = [r"\begin{tabular}{lrr}", r"\toprule",
             r"误差项 & BPF & ETPF \\", r"\midrule"]
    for label, metric in metrics:
        if metric == "post_state_mse":
            lines.append(r"\midrule")
        values = []
        for algorithm in ("bpf", "etpf"):
            value = summary[algorithm, metric]
            if metric == "resampling_disturbance":
                mantissa, exponent = f"{value:.2e}".split("e")
                values.append(rf"${mantissa}\times10^{{{int(exponent)}}}$")
            else:
                values.append(f"{value:.6f}")
        lines.append(label + " & " + " & ".join(values) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    (DATA / "error_table.tex").write_text("\n".join(lines) + "\n")
    manifest = {name: hashlib.sha256((DATA / name).read_bytes()).hexdigest()
                for name in ("summary.csv", "curves.csv", "collapse_summary.json", "checks.json")}
    (DATA / "plot_inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Generated Logistic figure and error table from archived results.")


if __name__ == "__main__":
    main()
