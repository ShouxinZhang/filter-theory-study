#!/usr/bin/env python3
"""使用 Markdown 模板和 C++ 评估输出生成可重复报告。"""
import json
import math
import sys
from pathlib import Path
from string import Template
from plots import figures, read_csv
from pipeline.common import atomic_json, digest_file
from pipeline.time_series import refresh_time_series

def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(x) for x in row) + " |" for row in rows)
    return "\n".join(lines)

def main(run_dir):
    run_dir = Path(run_dir)
    root = Path(__file__).resolve().parents[1]
    config = json.loads((run_dir / "config.json").read_text())
    metadata = json.loads((run_dir / "metadata.json").read_text())
    dataset = json.loads((run_dir / "dataset.json").read_text())
    execution = json.loads((run_dir / "execution.json").read_text())
    rows = read_csv(run_dir / "summary.csv")
    if not rows:
        raise RuntimeError("无完成结果，不能生成有效实验报告")
    refresh_time_series(run_dir)
    font_metadata = figures(run_dir, rows, config, dataset)
    env = metadata["environment"]
    peak = []
    for runtime in (run_dir / "jobs").rglob("*.runtime.csv"):
        peak.extend(float(r["peak_rss_kib"]) for r in read_csv(runtime))
    reference = [r for r in rows if
        (r["algorithm"] in ("kf", "ekf") or int(r["n"]) == config["reference_n"]) and
        (r["algorithm"] != "etpf" or math.isclose(float(r["epsilon"]), config["reference_epsilon"]))]
    metrics = [[r["algorithm"].upper(), r["interval"], r["trials"], "%.4f" % float(r["rmse"]),
        "[%.4f, %.4f]" % (float(r["ci_low"]), float(r["ci_high"])),
        "%.3f" % float(r["coverage"])] for r in reference]
    ot = [r for r in rows if r["algorithm"] == "etpf"]
    if ot:
        worst = max(float(r["ot_nonconverged_fraction"]) for r in ot)
        max_correction = max(float(r["rounding_l1_max"]) for r in ot)
        diagnostics = "ETPF 各配置未收敛更新比例最大为 %.1f%%，最大可行化 $L^1$ 修正为 %.4g，不能把未收敛配置视作精确求得熵正则最优解" % (worst * 100, max_correction)
    else:
        diagnostics = "本次未运行 ETPF"
    noise_description = (r"过程噪声 $\mathcal N(0,10)$，观测噪声 $\mathcal N(0,1)$" if config["dataset"]["model"] == "gordon"
                         else r"过程噪声 $\mathcal N(0,0.2)$，观测噪声 $\mathcal N(0,0.5)$")
    mapping = {
        "run_id": metadata["run_id"],
        "status": "完成 %s/%s 个作业，失败 %s 个，本次恢复跳过 %s 个" %
                  (execution["complete_jobs"], execution["expected_jobs"], execution["failed_jobs"], execution["skipped_jobs"]),
        "config_text": "模型 %s，冻结数据集 %s，共 %s 条轨迹，每条 %s 步\n\n$N=%s$，$\\varepsilon=%s$，观测间隔 $m=%s$，容差 %s，最大迭代 %s\n\n数据种子 %s，算法种子 %s，固定展示 $N=%s$，ETPF $\\varepsilon=%s$" %
            (config["dataset"]["model"], dataset["dataset_id"], config["dataset"]["trials"], config["dataset"]["steps"],
             config["particles"], config["epsilons"], config["intervals"], config["solver"]["tolerance"],
             config["solver"]["max_iterations"], config["dataset"]["seed"], config["algorithm_seed"],
             config["reference_n"], config["reference_epsilon"]) + "\n\n" + noise_description + r"，初始状态与滤波先验均为 $\mathcal N(0,2)$，括号第二项为方差",
        "environment_table": table(["项目", "记录"], [
            ["CPU", env["cpu"].get("Model name", "见metadata.json")],
            ["CPU核与线程", str(env["cpu"].get("Core(s) per socket", "?")) + "核 / " + str(env["cpu"].get("CPU(s)", "?")) + "线程"],
            ["操作系统", next((line.split("=", 1)[1].strip('"') for line in env["os_release"].splitlines() if line.startswith("PRETTY_NAME=")), "")],
            ["内核", env["kernel"]],
            ["系统可见总内存", "%.2f GiB" % (env["memory"]["MemTotal_kib"] / 1024**2)],
            ["单作业峰值RSS最大值", "%.2f MiB" % (max(peak, default=0) / 1024)],
            ["编译器", env["compiler"].splitlines()[0]],
            ["Eigen", env.get("eigen_version", "旧运行未记录")],
            ["任务并发 / 算法线程", "%s / %s" % (env["parallel_jobs"], env["threads_per_filter"])],
            ["源码SHA256", metadata["source"]],
        ]),
        "timing_mode": env["timing_mode"],
        "metrics_table": table(["算法", "观测间隔", "轨迹数", "RMSE", "95%置信区间", "95%区间覆盖率"], metrics),
        "diagnostics": diagnostics,
        "figure_style": "中文字体为宋体（SimSun），英文和数字为 " + font_metadata["latin_family"] + "，数学符号使用 MathText 与 STIX 字体渲染，PNG为300 dpi，另附字体转路径的SVG矢量图，字体路径和哈希见 report_metadata.json",
        "trajectory_description": (r"每组上图展示状态与滤波估计，下图展示原始观测 $y_k$ 和无噪声观测 $h(x_k)$；紫色圆点是算法实际收到的观测，灰色叉号是被当前帧率屏蔽的观测，仅供事后对照，两图共用时间轴。"
            + (r" Gordon 使用 $h(x_k)=x_k^2/20$，正负状态产生相同的无噪声观测，因此观测接近参考线也不能直接确定状态符号；观测点偏离参考线表示该次观测噪声。"
               if config["dataset"]["model"] == "gordon" else r" 线性模型使用 $h(x_k)=x_k$，观测点偏离参考线表示该次观测噪声。")),
        "time_series_definition": r"逐时刻曲线使用 $\mathrm{RMSE}_k=\sqrt{B^{-1}\sum_{b=1}^{B}(\widehat x_{k,b}-x_{k,b})^2}$，其中 $B$ 为完成的独立轨迹数，无观测步使用预测估计，有观测步使用更新估计，曲线未做平滑",
    }
    rendered = Template((root / "templates/report.md").read_text()).substitute(mapping)
    (run_dir / "report.md").write_text(rendered)
    # 报告可以在原实验上更新，新的评估与绘图版本独立留存
    atomic_json(run_dir / "report_metadata.json", {"font": font_metadata,
        "time_series_metadata_sha256": digest_file(run_dir / "time_series_metadata.json"),
        "report_source": {str(p.relative_to(root)): digest_file(p) for p in (
            root / "scripts/report.py", root / "scripts/plots.py", root / "scripts/plot_style.py",
            root / "scripts/plot_timeseries.py", root / "scripts/plot_trajectory.py", root / "templates/report.md")}})
    print("已生成图表和报告", run_dir / "report.md")

if __name__ == "__main__":
    main(sys.argv[1])
