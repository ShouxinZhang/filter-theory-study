数据来自 `../../../../2026-09-14_logistic-square-q0-control/runs/`，复用既有数值结果，未增加算法重复。
`summary.csv` 是四项误差与全时域 MSE，`curves.csv` 是逐时刻统计，`collapse_summary.json` 是单点贫化汇总，`checks.json` 是参考网格加密与数值恒等式检查。
原始运行参数和源码指纹见 `experiment_provenance.json`；作图输入 SHA-256 见 `plot_inputs.json`。
`error_table.tex` 和 `../../figures/logistic_robustness.pdf` 由 `../../scripts/logistic_plots.py` 生成。
图 (a) 将每 20 步 MSE 作不重叠分段平均，图 (b) 保留逐步平均不同位置数；不同位置按原 C++ 双精度值精确去重统计。
