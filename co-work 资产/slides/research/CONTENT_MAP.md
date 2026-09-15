# 六页正文的来源与取舍

源稿目录：`../../tex-build0906/`（相对本文件）。当前 deck 为 `../template/slides.md`，共 9 页。首页和致谢页保持任务开始时的用户版本。中间六页的正文均为可编辑 Markdown，显示公式由 KaTeX 渲染。

| 页码 | 主题 | 源文件与对应内容 |
| --- | --- | --- |
| 2 | 状态空间与 Bayes 递推 | `nonlinear_filtering.tex` 第 1–2 节：独立噪声，转移与似然，预测积分与 Bayes 更新 |
| 3 | BPF | `nonlinear_filtering.tex` 第 3 节，`algorithm_analysis.tex`：经验测度，先验提议，似然权重，重采样与缺测 |
| 4 | BPF 流程图 | 用户指定的 `2026-09-10_drawio-replicas/bpf/bpf.drawio`，同目录 SVG 原样插入 |
| 5 | 最优输运 | `ot_sinkhorn.tex` 第 4.1–4.2 节：Monge，Kantorovich，离散边缘，双向条件矩阵 |
| 6 | Sinkhorn 与 ETPF | `ot_sinkhorn.tex` 第 4.3–4.4 节，`algorithm_analysis.tex`：熵目标，缩放迭代，重心变换；均值恒等式由边缘约束直接推得 |
| 7 | 模型与精度 | `simulation.tex`，`simulation_assets/data/{config.json,accuracy.csv,time_series.csv}` |
| 8 | 分布与代价 | `simulation.tex`，`simulation_assets/data/{runtime.csv,accuracy.csv,kde/k11/*/density.csv,kde/provenance.json}` |

## 数学说明

BPF 原理展示独立多项式重采样，而仿真实现采用系统重采样，两者在第 3 页明确区分。给定旧粒子，从各混合层独立取样通常不具有同分布性，此细节保留在讲者备注。权重归一化需要似然和有限且为正。

离散条件矩阵的行是条件变量，列是被条件化变量。ETPF 取源边缘 a=w，目标边缘 b=1/N，T=NΠᵀ，并用分量公式避免源稿中行列粒子矩阵记法的歧义。重心变换在边缘精确时保持均值，但不保证协方差或整个分布不变。

原始 ETPF 的线性规划与正则化 ETPF 已区分；本实验使用后者。严格正核与正边缘的 Sinkhorn 收敛条件，不代表有限迭代一定达到数值容差。

## 实验数据范围

使用原运行 `quick-eb95c99ee644` 的 8 条冻结轨迹，每条 100 步。观测间隔 m=1,2,4,8。第 7 页表格选 N=500，ETPF ε=1；EKF 无粒子数参数。逐时 RMSE 图选 m=1，纵轴为对数轴。全时域 RMSE 是对所有轨迹与时刻的误差平方平均再开方。

m=1 时，BPF 的 RMSE 为 4.6478111，95% 整轨迹 bootstrap 区间约 [4.07,5.24]；ETPF 为 4.7110052，区间约 [4.05,5.37]。区间重叠本身不等于严格显著性检验，汇报仅表述当前数据未显示明确精度优势。

第 8 页密度图为 trial=0，k=11，N=500，m=1，ε=1，真值约 13.2261。粒子或集合方法分别使用 Scott 带宽，EKF 为解析高斯近似，不能凭峰高直接判定精度。

串行耗时固定逻辑 CPU0，Ryzen 9 9955HX3D，C++17/Eigen 双精度。每条轨迹重复 3 次取中位数，再跨 8 条轨迹求均值与样本标准差。ETPF/BPF 平均内核耗时比约 744.3；ETPF 有 23.13% 更新未在 1000 次迭代内达到 1e-8 容差，返回近似耦合并做边缘修正。NRMSE 与原 CSV 一致。

粒子数切片使用 m=1，ε=1。N=100,250,500 时 ETPF RMSE 分别约为 5.13,4.57,4.71，BPF 为 4.95,4.73,4.65。未把本组非单调性推广为普遍规律。

## 图表再生成

运行 `uv run --with matplotlib python research/prepare_simulation_figures.py`（在本项目根目录）。脚本读取同级 `tex-build0906` 的原 CSV，不重新运行仿真。所用表格与曲线数据复制到 `research/simulation-data/`，`provenance.json` 记录原输入路径与 SHA256。

SVG 图放在 `template/public/simulation/`，在 Slidev 中作为整体拖动和缩放。表格数字，标题，解释和公式直接保存在 Markdown。`research/middle-six-pages.md` 是本轮完成时的内容快照，后续人工编辑以 `template/slides.md` 为准。
