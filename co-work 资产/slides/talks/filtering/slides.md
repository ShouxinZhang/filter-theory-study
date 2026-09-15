---
theme: hitsz-academic
addons:
  - slide-sorter
  - image-paste
  - drawio-editor
title: 非线性滤波：神经网络与输运方法
author: 张守信
info: false
layout: hitsz-new-cover
defaults:
  layout: academic
  section: 非线性滤波
---

# 非线性滤波：输运方法

::details::

汇报人：张守信

导师：严质彬

哈尔滨工业大学（深圳），理学院数学系

硕士中期报告 · 2026 年 9 月 15 日

---
layout: academic
class: research-slide
section: 数学原理 · Bayes 递推
title: 非线性状态空间模型与 Bayes 递推
dragPos:
  heading: 42,32,896,48,0
  model: 42,100,432,167,0
  assumptions: 42,280,432,198,0
  prediction: 502,100,436,147
  bayes-update: 502,263,436,215,0
---

<v-drag pos="heading" class="research-heading">

# 非线性状态空间模型与 Bayes 递推

</v-drag>

<v-drag pos="model" class="research-block">

## 状态与观测

$$
\begin{aligned}
&X_k=f(X_{k-1},N_{x,k}),\\
&Y_k=h(X_k,N_{y,k}).
\end{aligned}
$$

$X_k\in\mathbb R^{n_x}$，$Y_k\in\mathbb R^{n_y}$。已知模型，初始分布与噪声分布，依次接收观测 $y_{1:k}$。

</v-drag>

<v-drag pos="assumptions" class="research-block">

**初始条件**:

- $X_0$ 与全部过程噪声 $N_{x,k}$，观测噪声 $N_{y,k}$相互独立。
- 密度存在，似然可算，归一化项有限且为正。

**输入**: 模型 $f,h$，初始分布 $\mathbb{P}_{X_0}$，噪声分布 $\mathbb{P}_{N_x},\mathbb{P}_{N_y}$，依次到达的观测值 $y_1,y_2,\dots$

**输出**: 后验分布 $p(x_k\mid y_{1:k})$

</v-drag>

<v-drag pos="prediction" class="research-block">

## 预测：对上一时刻后验积分

$$
\begin{aligned}
&p(x_k\mid y_{1:k-1})\\
= &\int p(x_k\mid x_{k-1})p(x_{k-1}\mid y_{1:k-1})\,\mathrm d x_{k-1}.
\end{aligned}
$$

</v-drag>

<v-drag pos="bayes-update" class="research-block">

## 更新：似然加权与归一化

记 $g_k(x)=p_{Y_k\mid X_k}(y_k\mid x)$。

$$
p(x_k\mid y_{1:k})=
\frac{g_k(x_k)p(x_k\mid y_{1:k-1})}
{\int g_k(z)p(z\mid y_{1:k-1})\,\mathrm d z}.
$$

以 $p(x_0)$ 初始化，更新后的后验进入下一轮预测。非线性模型中的积分通常无闭式表达。

</v-drag>

<!--
内容来源：tex-build0906/nonlinear_filtering.tex，第1–2节，式(1)–(4)。g_k 的定义沿用 algorithm_analysis.tex。
此页 d x 对应原稿欧氏状态空间体积测度 d v_X。各内容块的坐标由 dragPos 保存。
-->

---
layout: academic
class: research-slide
section: 数学原理 · 粒子滤波
title: 经验测度近似与自举粒子滤波
dragPos:
  heading: 42,32,896,48,0
  particle-predict: 42,100,432,197,0
  random-resampling: 42,310,432,173,0
  particle-update: 502,100,334,226
  resampling-meaning: 502,338,436,156,0
---

<v-drag pos="heading" class="research-heading">

# 经验测度近似与自举粒子滤波

</v-drag>

<v-drag pos="particle-predict" class="research-block">

## 预测：把积分改为样本平均

等权后验 $\hat{\mathbb P}_{N;X_{k-1}}^+=\frac1N\sum_i\delta_{X_{k-1}^{+,(i)}}$。

转移先验提议 $q=p(x_k\mid x_{k-1})$：

$$
\begin{aligned}
&x_k^{-,(i)}=f(x_{k-1}^{+,(i)},n_{x,k}^{(i)}),\\
&\hat{\mathbb P}_{N;X_k}^-=\frac1N\sum_i\delta_{_k^{-,(i)}}.
\end{aligned}
$$



</v-drag>

<v-drag pos="random-resampling" class="research-block">

## BPF：用复制次数表达后验质量

$$
\begin{aligned}
&\mathbb P(A_j=i\mid\bm{w}_k^+)=w_k^{+,(i)},\\
&x_k^{+,(j)}=x_k^{-,(A_j)},\;w_k^{(j)}=1/N.
\end{aligned}
$$

基本版本独立抽取 $A_1,\ldots,A_N$，高权重粒子更易被复制。仿真实现采用系统重采样或多项式采样。

</v-drag>

<v-drag pos="particle-update" class="research-block">

## 更新：粒子位置不变，更新权重

$$
\begin{aligned}
&w_k^{+,(i)}=\frac{g_k(x_k^{-,(i)})}{\sum_r g_k(x_k^{-,(r)})},\\
&\hat{\mathbb P}_{N;X_k}^+=\sum_iw_k^{+,(i)}\delta_{x_k^{-,(i)}},\\
&\widehat x_k=\sum_iw_k^{+,(i)}x_k^{-,(i)}.
\end{aligned}
$$

似然和有限且为正；重采样前输出均值。

</v-drag>

<v-drag pos="resampling-meaning" class="research-block">

## 重采样的作用与代价

固定预测粒子与权重，设复制次数为 $n_i$：

$$
\mathbb E[n_i/N\mid\bm w_k^+]=w_k^{+,(i)}.
$$

重采样恢复等权表示，但一次实现会引入随机误差并产生重复粒子。

</v-drag>

<!--
来源：nonlinear_filtering.tex 第3节；algorithm_analysis.tex 的 BPF 伪代码与间隔观测说明。
注意：算法原理中的独立重采样与 simulation.tex 中的系统重采样作了区分。
给定旧粒子，从各转移混合层独立取样，通常不同分布。
-->

---
layout: academic
class: research-slide
section: 算法分析 · BPF 流程
title: BPF：预测，似然加权与独立重采样
dragPos:
  bpf-flowchart: 160,7,660,500
---

<v-drag pos="bpf-flowchart" class="research-figure">

<DrawioDiagram id="bpf" src="/diagrams/bpf.svg" alt="BPF：预测，似然加权与独立重采样流程图" />

</v-drag>

<!--
图源：2026-09-10_drawio-replicas/bpf/bpf.drawio；同目录 bpf.svg 为已导出的预览。
图示为每步观测下的独立重采样版本；后续仿真 BPF 采用系统重采样。
-->

---
layout: academic
class: research-slide
section: 算法分析 · ETPF 流程
title: ETPF：最优输运与重心变换
dragPos:
  etpf-flowchart: 160,7,660,500
---

<v-drag pos="etpf-flowchart" class="research-figure">

<DrawioDiagram id="etpf" src="/diagrams/etpf.svg" alt="ETPF：最优输运与重心变换流程图" />

</v-drag>

<!--
图源：2026-09-10_drawio-replicas/etpf/etpf.drawio 与 etpf.svg。
依据 algorithm_analysis.tex 中的原始 ETPF：以离散最优耦合做重心变换。
此图为无熵正则的最优输运目标；后文 Sinkhorn 为正则化近似设置。
-->

---
layout: academic
class: research-slide
section: 新增内容
title: 新页面
dragPos:
  heading: 42,32,896,48,0
  left-column: 42,100,607,191
  right-column: 502,297,436,153
  coupling: 521,181,413,205
  monge: 38,185,390,194
---

<v-drag pos="heading" class="research-heading">

# 重采样步骤的核心理论

</v-drag>

<v-drag pos="left-column" class="research-block">

从离散分布 $(x_{k}^{-,(i)},w_{k}^{(i)})$ 变换为均匀离散分布 $(x_{k}^{+,(i)},1/N)$

因而，可以视为不同分布之间的输运问题

</v-drag>

<v-drag pos="monge" class="research-block">

## Monge：确定性搬运

$$
\begin{aligned}
&T_*\mathbb P_X=\mathbb P_Y,\\
&\inf_{T:\,T_*\mathbb P_X=\mathbb P_Y}
\int c(x,T(x))\,\mathrm d\mathbb P_X(x).
\end{aligned}
$$

每个源点的质量只能整体送往一个目标点。离散边缘下，可行映射未必存在。

</v-drag>

<v-drag pos="coupling" class="research-block">

## Kantorovich：概率分流松弛

用联合分布 $\mu$ 代替确定性映射：

$$
\begin{aligned}
&(\pi_1)_*\mu=\mathbb P_X,\;(\pi_2)_*\mu=\mathbb P_Y,\\
&\inf_{\mu\in\Pi(\mathbb P_X,\mathbb P_Y)}
\int c(x,y)\,\mathrm d\mu(x,y).
\end{aligned}
$$

$\pi_1,\pi_2$ 是坐标投影。这里的 $Y$ 是输运目标变量，不是滤波观测。

</v-drag>

---
layout: academic
class: research-slide
section: 数学原理 · 最优输运
title: 从 Monge 映射到离散耦合
dragPos:
  heading: 42,32,896,48,0
  monge: 42,100,432,170,0
  coupling: 42,283,432,199,0
  discrete-ot: 502,100,436,202,0
  conditional: 502,313,436,181,0
---

<v-drag pos="heading" class="research-heading">

# 从 Monge 映射到离散耦合

</v-drag>

<v-drag pos="monge" class="research-block">

## Monge：确定性搬运

$$
\begin{aligned}
&T_*\mathbb P_X=\mathbb P_Y,\\
&\inf_{T:\,T_*\mathbb P_X=\mathbb P_Y}
\int c(x,T(x))\,\mathrm d\mathbb P_X(x).
\end{aligned}
$$

每个源点的质量只能整体送往一个目标点。离散边缘下，可行映射未必存在。

</v-drag>

<v-drag pos="coupling" class="research-block">

## Kantorovich：概率分流松弛

用联合分布 $\mu$ 代替确定性映射：

$$
\begin{aligned}
&(\pi_1)_*\mu=\mathbb P_X,\;(\pi_2)_*\mu=\mathbb P_Y,\\
&\inf_{\mu\in\Pi(\mathbb P_X,\mathbb P_Y)}
\int c(x,y)\,\mathrm d\mu(x,y).
\end{aligned}
$$

$\pi_1,\pi_2$ 是坐标投影。这里的 $Y$ 是输运目标变量，不是滤波观测。

</v-drag>

<v-drag pos="discrete-ot" class="research-block">

## 离散耦合与边缘约束

源质量 $\bm{a}$，目标质量 $\bm{b}$。

$$
\begin{aligned}
&\Pi_{ij}=\mathbb P(X=x_i,Y=y_j),\\
&\bm\Pi\bm1_n=\bm{a},\;
\bm\Pi^{\mathsf T}\bm1_m=\bm{b},\\
&U(\bm{a},\bm{b})=\{\bm\Pi\geq0:\text{满足上述边缘}\},\\
&\min_{\bm\Pi\in U(\bm a,\bm b)}
\sum_{i,j}\Pi_{ij}C_{ij},\;C_{ij}=c(x_i,y_j).
\end{aligned}
$$

</v-drag>

<v-drag pos="conditional" class="research-block">

## 从联合质量得到条件权重

正边缘 $a_i,b_j>0$：

$$
\begin{aligned}
&P_{Y\mid X;i,j}=\Pi_{ij}/a_i,\\
&P_{X\mid Y;j,i}=\Pi_{ij}/b_j.
\end{aligned}
$$

行是条件变量，列是被条件化变量；重心变换用第二式。

</v-drag>

<!--
来源：ot_sinkhorn.tex 第4.1–4.2节，Monge，Kantorovich，离散边缘与条件概率矩阵。
两组支撑点各自互异，边缘归一化。未展开附录中的离散 Monge 整除条件证明。
-->

---
layout: academic
class: research-slide
section: 数学原理 · Sinkhorn 与 ETPF
title: 熵正则化，Sinkhorn 与重心变换
dragPos:
  heading: 42,32,896,48,0
  entropy: 42,98,432,193,0
  sinkhorn: 42,301,432,189,0
  etpf: 502,98,436,214,0
  mean-preservation: 502,324,436,166,0
---

<v-drag pos="heading" class="research-heading">

# 熵正则化，Sinkhorn 与重心变换

</v-drag>

<v-drag pos="entropy" class="research-block">

## 正则化后的输运目标

$$
\min_{\bm\Pi\in U(\bm a,\bm b)}
\left\{\langle\bm\Pi,\bm C\rangle_F
+\varepsilon\sum_{i,j}\Pi_{ij}(\log\Pi_{ij}-1)\right\}.
$$

固定边缘时，负熵与 $D_{\mathrm{KL}}(\bm\Pi\|\bm a\bm b^{\mathsf T})$ 仅差常数。

$$
\begin{aligned}
&K_{ij}=\exp(-C_{ij}/\varepsilon),\\
&\bm\Pi=\operatorname{diag}(\bm u)\bm K\operatorname{diag}(\bm v).
\end{aligned}
$$

</v-drag>

<v-drag pos="sinkhorn" class="research-block">

## 交替校正两侧边缘

从 $\bm v^{(0)}=\bm1$ 开始，逐元素相除：

$$
\begin{aligned}
&\bm u^{(\ell+1)}=\bm a\oslash(\bm K\bm v^{(\ell)}),\\
&\bm v^{(\ell+1)}=\bm b\oslash(\bm K^{\mathsf T}\bm u^{(\ell+1)}).
\end{aligned}
$$

两侧边缘残差均小于 $\tau$ 时停止。严格正核与正边缘下收敛，数值实现仍需检查残差与迭代上限。

</v-drag>

<v-drag pos="etpf" class="research-block">

## ETPF：从加权粒子生成等权粒子

$$
\begin{aligned}
&\bm a=\bm w_k^+,\;\bm b=\bm1_N/N,\\
&C_{ij}=\|x_k^{-,(i)}-x_k^{-,(j)}\|^2,\\
&x_k^{+,(j)}=N\sum_i\Pi_{k;ij}x_k^{-,(i)}.
\end{aligned}
$$

列和为 $1/N$，新粒子是以 $N\Pi_{k;ij}$ 为权重的条件均值。

</v-drag>

<v-drag pos="mean-preservation" class="research-block">

## 均值守恒（边缘精确时）

$$
\frac1N\sum_jx_k^{+,(j)}=\sum_iw_k^{+,(i)}x_k^{-,(i)}.
$$

原始 ETPF 计算线性规划；仿真使用 $\varepsilon>0$ 的正则化版本。

</v-drag>

<!--
来源：ot_sinkhorn.tex 第4.3–4.4节；algorithm_analysis.tex 的 ETPF 与 Sinkhorn 伪代码。
均值恒等式由源边缘求和直接推出，是这里写出的推论，不是独立的实验结论。
-->

---
layout: academic
class: research-slide
section: 仿真总结 · 模型与精度
title: Gordon 基准：实验设置与估计精度
dragPos:
  heading: 42,32,896,48,0
  benchmark: 42,96,436,197,0
  experiment: 42,296,436,94,0
  accuracy: 502,341,436,151,0
  rmse-figure: 502,100,436,241,0
  accuracy-findings: 42,398,436,92,0
---

<v-drag pos="heading" class="research-heading">

# Gordon 基准：实验设置与估计精度

</v-drag>

<v-drag pos="benchmark" class="research-block">

## 一维非线性模型

$$
\begin{aligned}
&X_k=\tfrac12X_{k-1}+\frac{25X_{k-1}}{1+X_{k-1}^2}\\
&\hspace{1em}+8\cos(1.2(k-1))+N_{x,k},\\
&Y_k=X_k^2/20+N_{y,k}.
\end{aligned}
$$

$X_0\sim\mathcal N(0,2)$，$N_{x,k}\sim\mathcal N(0,10)$，$N_{y,k}\sim\mathcal N(0,1)$，第二参数为方差。

</v-drag>

<v-drag pos="experiment" class="research-block compact-copy">

8 条轨迹 × 100 步，共享冻结数据。观测间隔 $m=1,2,4,8$，缺测步只预测。

$N=500$，ETPF $\varepsilon=1$；右图为 $m=1$。

</v-drag>

<v-drag pos="accuracy" class="research-block research-table">

## 全时域 RMSE（$N=500$）

| 方法 | $m=1$ | $m=2$ | $m=4$ | $m=8$ |
| --- | ---: | ---: | ---: | ---: |
| EKF | 17.80 | 22.80 | 40.85 | 16.67 |
| BPF | 4.65 | 6.44 | 7.46 | 8.14 |
| EnKF | 5.12 | 6.71 | 7.94 | 8.39 |
| ETPF | 4.71 | 6.41 | 7.50 | 8.14 |

</v-drag>

<v-drag pos="rmse-figure" class="research-figure">

![每步观测 m=1 时，四算法逐时刻跨轨迹 RMSE](/simulation/rmse-m1.svg)

</v-drag>

<v-drag pos="accuracy-findings" class="research-block compact-copy">

## 精度比较

$m=1$ 时，BPF 与 ETPF 的 RMSE 为 4.65 与 4.71，95% bootstrap 区间重叠，未见明确精度优势。

</v-drag>

<!--
来源：simulation.tex 的模型与时序误差分析；simulation_assets/data/config.json，accuracy.csv，time_series.csv。
m=1 的95%区间：BPF约[4.07,5.24]，ETPF约[4.05,5.37]。
RMSE=sqrt(sum_{b,k}(estimate-truth)^2/(BK))。区间为整条轨迹 bootstrap 1000 次，未将重叠本身当作严格显著性检验。
图由 research/prepare_simulation_figures.py 从原 CSV 选择 m=1 重绘，未重新模拟。EKF 无粒子数参数。
-->

---
layout: academic
class: research-slide
section: 仿真总结 · 分布与代价
title: 后验形状与串行计算代价
dragPos:
  heading: 42,32,896,48,0
  density-figure: 42,101,436,241,0
  density-findings: 42,350,436,144,0
  runtime: 502,98,436,227,0
  ablation-findings: 502,336,436,164,0
---

<v-drag pos="heading" class="research-heading">

# 后验形状与串行计算代价

</v-drag>

<v-drag pos="density-figure" class="research-figure">

![首条轨迹 k=11，N=500，m=1 时的更新后分布](/simulation/posterior-k11.svg)

</v-drag>

<v-drag pos="density-findings" class="research-block">

## 首条轨迹，$k=11$

BPF 与 ETPF 均呈双峰；EKF 为单峰。

</v-drag>

<v-drag pos="runtime" class="research-block research-table">

## 每步内核耗时（$\mu\mathrm s$）

| 方法 | 均值 ± 标准差 | NRMSE |
| --- | ---: | ---: |
| EKF | 0.104 ± 0.003 | 167.87% |
| BPF | 38.013 ± 0.100 | 43.83% |
| EnKF | 49.680 ± 0.125 | 48.32% |
| ETPF | 28,293.091 ± 2,576.275 | 44.43% |

<div class="compact-copy">

$m=1,N=500,\varepsilon=1$，固定单逻辑核计时。ETPF 耗时约为 BPF 的 744 倍，迭代未达标率 23.13%（上限 1000 次，容差 $10^{-8}$）。

</div>

</v-drag>

<v-drag pos="ablation-findings" class="research-block research-table compact-copy">

## 粒子数切片（$\varepsilon=1$）

| RMSE | $N=100$ | $250$ | $500$ |
| --- | ---: | ---: | ---: |
| BPF | 4.95 | 4.73 | 4.65 |
| ETPF | 5.13 | 4.57 | 4.71 |

ETPF 误差非单调，未见明确精度收益。

</v-drag>

<!--
来源：simulation.tex 的计算开销，单因素切片与后验密度分析。
数据：runtime.csv，accuracy.csv，kde/k11/{bpf,enkf,etpf}/density.csv，kde/provenance.json。
CPU为 Ryzen 9 9955HX3D，固定逻辑CPU0，C++17/Eigen，双精度。每轨迹3次中位数，再汇总8轨迹均值±样本标准差。
耗时比=28293.091430000004/38.013227500000006，约744.3。未收敛不等于程序失败：返回近似耦合并做边缘修正。
密度图来源原试验 trial=0，N=500，epsilon=1，m=1；红色 EKF 曲线为高斯近似，竖线为真值。
-->

---
layout: academic
class: research-slide
section: 仿真总结 · 零过程噪声
title: 零过程噪声 Logistic 模型：粒子贫化与稳健性
dragPos:
  heading: 42,32,896,48,0
  logistic-model: 42,100,326,194,0
  logistic-results: 42,316,326,170,0
  logistic-figure: 390,96,548,219,0
  logistic-findings: 390,328,548,167,0
---

<v-drag pos="heading" class="research-heading">

# 零过程噪声 Logistic 模型：粒子贫化与稳健性

</v-drag>

<v-drag pos="logistic-model" class="research-block">

## 模型与设置

$$
\begin{aligned}
&X_k=4X_{k-1}(1-X_{k-1}),\\
&Y_k=X_k^2+N_{y,k},\\
&N_{y,k}\sim\mathcal N(0,0.1).
\end{aligned}
$$

$X_0\sim U[0,1]$，$N=128$，每步观测。

64 条路径 × 1000 步 × 32 次独立运行。

</v-drag>

<v-drag pos="logistic-results" class="research-block research-table">

## 误差与粒子多样性

| 指标 | BPF | ETPF |
| --- | ---: | ---: |
| 总 MSE | 0.247544 | 0.072128 |
| 单点贫化运行 | 2048/2048 | 0/2048 |
| 末步不同位置数 | 1 | 69.67 |

<div class="compact-copy">

MSE 为第 1–1000 步平均。  
位置数为末步跨运行均值。

</div>

</v-drag>

<v-drag pos="logistic-figure" class="research-figure">

![零过程噪声 Logistic 模型的均方误差与不同粒子位置数](/simulation/logistic-robustness.png)

</v-drag>

<v-drag pos="logistic-findings" class="research-block">

## 极端情况下，ETPF 保留粒子多样性

- 总 MSE 降低 **70.9%**；2048 次运行均未发生单点贫化。
- BPF：每步多项式重采样；ETPF：一维无正则最优输运。

</v-drag>

<!--
来源：tex-build0906/simulation_logistic.tex；simulation_assets/data/logistic/summary.csv、collapse_summary.json、error_table.tex。
图源：simulation_assets/figures/logistic_robustness.png；原图由 logistic_plots.py 根据已有仿真结果生成。
图 (a) MSE 按每 20 步分段平均；Bayes 曲线为参考风险。图 (b) 横轴为对数尺度，不同位置数为跨运行平均。
零噪声仅指过程噪声为零；观测噪声方差为 0.1。
实测重采样后总 MSE：BPF 0.24754431889453974，ETPF 0.072128049575117263，降低 70.8625712%。
2048=64 条观测路径×每条32次算法运行；ETPF 末步不同位置数均值为 69.66650390625。
本实验为一维无正则最优输运，不能将收益直接推广至所有模型或前述 Sinkhorn 参数设置。
-->

---
layout: academic
class: research-slide
section: 后续工作
title: What's next?
dragPos:
  heading: 42,32,896,48,0
  next-theory: 42,106,896,98,0
  next-algorithm: 42,232,896,98,0
  next-simulation: 36,347,896,120
---

<v-drag pos="heading" class="research-heading">

# <span lang="en" style="font-family: Arial, sans-serif">What's next?</span>

</v-drag>

<v-drag pos="next-theory" class="research-block">

## 更完善的数学原理

- 完善误差分析理论
- 极端情况下的更多分析

</v-drag>

<v-drag pos="next-algorithm" class="research-block">

## 更快的算法
- 矩阵分解
- 神经网络

</v-drag>

<v-drag pos="next-simulation" class="research-block">

## 更复杂的仿真环境

- 拓展至高维、强非线性、多峰后验与稀疏观测。
- 更动态多样的游戏环境

</v-drag>



<v-drag id="pasted-202ef962-ad65-4535-8ba5-62db81ed76dc" pos="486,22,465,459" class="pasted-image">

![粘贴图片](/images/pasted-202ef962-ad65-4535-8ba5-62db81ed76dc.png)

</v-drag>

---
layout: academic
class: academic-thanks
background: /images/thanks-background.png
section: 致谢
title: 致谢
---

# 谢谢各位老师

敬请批评指正
