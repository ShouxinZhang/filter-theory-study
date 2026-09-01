
# Sinkhorn 距离：最优传输的光速计算

**Marco Cuturi**
京都大学情报学研究科
mcuturi@i.kyoto-u.ac.jp

---

### 摘要

最优传输（Optimal Transport）距离是用于比较概率测度与特征直方图的一类基础距离。尽管它们具有吸引人的理论性质、在检索任务中的出众表现以及直观的公式表述，但其计算依赖于线性规划的求解；一旦测度支撑集的大小或直方图的维度超过数百，求解成本便会迅速变得难以承受。本文提出了一类全新的最优传输距离，从最大熵的视角重新审视传输问题。我们利用熵正则化项平滑了经典的最优传输问题，并证明所得的最优解依然是一个距离，该距离可以通过 Sinkhorn 矩阵缩放算法进行计算，其求解速度比传统传输求解器快数个数量级。我们还表明，在 MNIST 分类问题上，这种正则化距离较经典最优传输距离表现更佳。

---

### 1 引言

选择合适的距离来比较概率分布是统计机器学习中的核心问题。当对概率分布所依托的概率空间知之甚少时，人们提出了假设极少的各种信息散度（Information Divergence）来充当这一角色，包括 Hellinger 散度、$\chi^2$ 散度、全变差（Total Variation）以及 Kullback-Leibler (KL) 散度。当概率空间为度量空间时，最优传输距离（Villani, 2009, §6，在计算机视觉中亦被称为推土机距离 EMD；Rubner et al., 1997）提供了一种用于比较概率的更为强大的几何工具。

然而，这种强大的表达能力伴随着高昂的计算代价。无论采用何种算法——网络单纯形法或内点法——在一般度量空间中比较两个维度为 $d$ 的直方图或两个规模为 $d$ 的点云时，计算最优传输距离的时间复杂度至少为 $O(d^3 \log d)$（Pele and Werman, 2009, §2.1）。

在特定的情形下，若所关注的度量概率空间可以嵌入到 $\mathbb{R}^n$ 且 $n$ 较小，则计算或近似最优传输距离可以变得相当高效。事实上，当 $n = 1$ 时，其计算仅需 $O(d \log d)$ 次操作。当 $n \ge 2$ 时，可利用测度嵌入在线性时间内对其进行近似（Indyk and Thaper, 2003; Grauman and Darrell, 2004; Shirdhonkar and Jacobs, 2008），且网络单纯形求解器经修改后可在二次时间内运行（Gudmundsson et al., 2007; Ling and Okada, 2007）。然而，此类嵌入带来的失真（Naor and Schechtman, 2007）以及随着 $n$ 的增加上述修改导致的成本指数级上升，使得这些方法在 $n > 4$ 时不再适用。超出上述特殊范围后，在任意度量空间中计算支撑集仅为数百个点/箱（bin）的一对测度之间的单次距离，在单核 CPU 上可能就需要数秒以上的时间。该瓶颈严重阻碍了最优传输距离在大规模数据分析中的应用，甚至让人质疑其在当今高维直方图与高维空间测度盛行的机器学习领域的实用价值。

本文表明，可以采取另一种策略来加速最优传输的计算，甚至有可能在推理任务中定义出更好的距离。无论原始概率空间的度量特性如何，我们的策略均成立。我们没有选择利用目标度量概率空间的性质（例如能否嵌入到低维欧氏空间中），而是选择直接聚焦于原始传输问题本身，并使用熵正则化项对其进行正则化。我们指出，鉴于最优传输问题的几何结构，这种正则化是非常直观的；事实上，在传输理论中，它长期以来一直被用于预测交通流模式并备受青睐（Wilson, 1969）。从优化的角度看，该正则化具有诸多优点，其中最核心的是将传输问题转化为一个严格凸优化问题，从而可以通过矩阵缩放（Matrix Scaling）算法求解。这类算法包括 Sinkhorn 著名的不动点迭代（1967），该方法已知具有线性收敛速度（Franklin and Lorenz, 1989; Knight, 2008）。与其他需要循环执行复杂条件判断语句的类似单纯形法的迭代方法不同，Sinkhorn 算法的执行仅依赖于矩阵-向量乘法。我们提出了该算法的一种新颖实现，能够利用矩阵-矩阵乘法*同时*计算单个点到一组点族的距离，因此非常适合在 GPGPU 架构上实现。我们表明，在 MNIST 手写数字分类的基准任务中，正则化距离的表现优于标准最优传输距离，且计算速度提升了数个数量级。

本文的结构安排如下：第 2 节回顾最优传输理论的基础知识；第 3 节引入 Sinkhorn 距离；第 4 节提供算法细节；第 5 节展开实证研究，最后给出结论。

---

### 2 最优传输理论回顾

#### 传输多面体及其联合概率解释

在下文中，$\langle \cdot, \cdot \rangle$ 表示 Frobenius 内积。对于单形 $\Sigma_d := \{x \in \mathbb{R}^d_+ : x^{\mathrm{T}} \mathbf{1}_d = 1\}$ 中的两个概率向量 $r$ 和 $c$（其中 $\mathbf{1}_d$ 为 $d$ 维全 1 向量），我们将 $r$ 和 $c$ 的传输多面体（即由 $d \times d$ 矩阵构成的多面体集）记为 $U(r,c)$：

$$
U(r,c) := \{ P \in \mathbb{R}^{d \times d}_+ \mid P \mathbf{1}_d = r, \, P^{\mathrm{T}} \mathbf{1}_d = c \}
$$

$U(r,c)$ 包含了所有行和与列和分别为 $r$ 和 $c$ 的非负 $d \times d$ 矩阵。$U(r,c)$ 具有明确的概率解释：对于取值于 $\{1, \dots, d\}$ 且边际分布分别为 $r$ 和 $c$ 的两个多项随机变量 $X$ 和 $Y$，集合 $U(r,c)$ 包含了 $(X, Y)$ 所有可能的*联合概率*。事实上，任意矩阵 $P \in U(r,c)$ 都可以对应为 $(X, Y)$ 的一个联合概率分布，使得 $p(X=i, Y=j) = p_{ij}$。我们定义 $P, Q \in U(r,c)$ 的熵 $h$ 和 KL 散度（Kullback-Leibler divergence），以及边际分布 $r \in \Sigma_d$ 的熵如下：

$$
h(r) = -\sum_{i=1}^d r_i \log r_i, \quad h(P) = -\sum_{i,j=1}^d p_{ij} \log p_{ij}, \quad \mathrm{KL}(P \| Q) = \sum_{ij} p_{ij} \log \frac{p_{ij}}{q_{ij}}
$$

#### $r$ 与 $c$ 之间的最优传输距离

给定一个 $d \times d$ 的代价矩阵 $M$，使用传输矩阵（或联合概率）$P$ 将 $r$ 映射到 $c$ 的代价可以量化为 $\langle P, M \rangle$。公式 (1) 定义的问题：

$$
d_M(r,c) := \min_{P \in U(r,c)} \langle P, M \rangle \tag{1}
$$

被称为给定代价 $M$ 下，$r$ 与 $c$ 之间的*最优传输（Optimal Transport, OT）*问题。该问题的最优表 $P^*$ 可以通过网络单纯形法（Network Simplex; Ahuja et al., 1993, §9）等方法求解。当矩阵 $M$ 本身是一个度量矩阵（即 $M$ 属于距离矩阵锥；Avis, 1980; Brickell et al., 2008）时，该问题的极值 $d_M(r,c)$ 即构成 $r$ 与 $c$ 之间的某种距离（Villani, 2009, §6.1）：

$$
\mathcal{M} = \{ M \in \mathbb{R}^{d \times d}_+ \mid \forall i,j \le d, \, m_{ij} = 0 \iff i = j; \; \forall i,j,k \le d, \, m_{ij} \le m_{ik} + m_{kj} \}
$$

对于一般的代价矩阵 $M$，利用目前提出的最佳算法计算该最优解时，最坏情况下的时间复杂度为 $O(d^3 \log d)$，且在实际应用中亦表现为超三次（super-cubic）复杂度（Pele and Werman, 2009, §2.1）。

### 3 Sinkhorn 距离：带有熵约束的最优传输

#### 联合概率上的熵约束

对于联合概率分布，以下信息论不等式（Cover and Thomas, 1991, §2）是紧致的：

$$
\forall r,c \in \Sigma_d, \, \forall P \in U(r,c), \, h(P) \le h(r) + h(c)
$$

这是因为*独立表* $r c^{\mathrm{T}}$（Good, 1963）的熵满足 $h(r c^{\mathrm{T}}) = h(r) + h(c)$。基于熵的凹性，我们可以引入如下凸集：

$$
U_\alpha(r,c) := \{ P \in U(r,c) \mid \mathrm{KL}(P \| r c^{\mathrm{T}}) \le \alpha \} = \{ P \in U(r,c) \mid h(P) \ge h(r) + h(c) - \alpha \} \subset U(r,c)
$$

上述两个定义确实是等价的，因为很容易验证 $\mathrm{KL}(P \| r c^{\mathrm{T}}) = h(r) + h(c) - h(P)$；若两随机变量 $(X, Y)$ 服从联合概率 $P$，该项恰好也是其互信息 $I(X; Y)$（Cover and Thomas, 1991, §2）。因此，将到 $r c^{\mathrm{T}}$ 的 KL 散度限制在某一阈值以下的矩阵集合 $P$，可以解释为 $U(r,c)$ 中相对于 $h(r)$ 和 $h(c)$ 具有*充分熵*、或具有足够小*互信息*的联合概率集合。基于将在第 4 节中阐明的理由，我们将下式定义为 $r$ 与 $c$ 之间的 Sinkhorn 距离：

**定义 1（Sinkhorn 距离）**.

$$
d_{M,\alpha}(r,c) := \min_{P \in U_\alpha(r,c)} \langle P, M \rangle
$$

为什么要在最优传输中引入熵约束？第一个原因源于计算效率（详见第 4 节）。第二个原因基于如下直觉：作为线性规划的经典结论，OT 问题的解总是落在 $U(r,c)$ 的顶点上。这类顶点是稀疏的 $d \times d$ 矩阵，其非零元素最多仅有 $2d - 1$ 个（Brualdi, 2006, §8.1.3）。从概率角度看，这类顶点代表了准确定性（quasi-deterministic）的联合概率，因为若 $p_{ij} > 0$，通常对于 $j \neq j'$ 的 $p_{ij'}$ 极少非零。我们主张将对低代价联合概率的搜索限制在具有充分平滑度的表内，而非将 $U(r,c)$ 的此类极端顶点作为 OT 距离的基础。值得注意的是，若我们在约束传输代价的同时最大化熵，这等价于考虑最大熵原理（Jaynes, 1957; Darroch and Ratcliff, 1972）。

在进一步阐述 Sinkhorn 距离的性质之前，我们注意到 Ferradans 等人（2013）近期也探索了类似的思想。他们在颜色匹配问题中，通过基于图的范数对原始传输问题进行松弛和惩罚，以避免原始最优解表现出的不良性质。结合来看，他们的想法与我们的方法均表明：在计算和建模需求的双重驱动下，更多平滑正则化项在求解 OT 问题中的应用值得深入研究。

#### Sinkhorn 距离的度量性质

当 $\alpha$ 足够大时，Sinkhorn 距离与经典 OT 距离重合。当 $\alpha = 0$ 时，Sinkhorn 距离存在闭式解；若假设 $M$ 本身是一个负定距离（或等价地，为欧氏距离矩阵），Sinkhorn 距离则成为一个负定核（Negative Definite Kernel）。

**性质 1**. *对于足够大的 $\alpha$，Sinkhorn 距离 $d_{M,\alpha}$ 即为传输距离 $d_M$。*

*证明*. 由于对任意 $P \in U(r,c)$，$h(P)$ 均有下界 $\frac{1}{2}(h(r) + h(c))$，因此当 $\alpha$ 足够大时，有 $U_\alpha(r,c) = U(r,c)$，两极值完全重合。$\blacksquare$

**性质 2（独立核）**. *$d_{M,0} = r^{\mathrm{T}} M c$。若 $M$ 为欧氏距离矩阵，则 $d_{M,0}$ 为负定核，且独立核 $e^{-t d_{M,0}}$ 对所有 $t > 0$ 均为正定核。*

证明见附录。除这两个极限情况外，本节的主定理指出：对于所有可能的 $\alpha$ 值，Sinkhorn 距离均保持对称性并满足三角不等式。由于对足够小的 $\alpha$，只要 $h(r) > 0$ 即可推得 $d_{M,\alpha}(r,r) > 0$，因此 Sinkhorn 距离无法严格满足自反性公理（即对所有 $x, y$，$\mathrm{d}(x,y) = 0 \iff x = y$）。然而，若有需要，只需将 $d_{M,\alpha}$ 乘以示性函数 $\mathbf{1}_{r \neq c}$ 即可恢复自反性。

**定理 1**. *对任意 $\alpha \ge 0$ 及 $M \in \mathcal{M}$，$d_{M,\alpha}$ 是对称的且满足所有三角不等式。函数 $(r,c) \mapsto \mathbf{1}_{r \neq c} d_{M,\alpha}(r,c)$ 满足全部三条距离公理。*

---

![图 1 传输多面体与 KL 球](figures/sinkhorn-distances/fig1.png)

> **图 1**：传输多面体 $U(r,c)$ 以及以 $r c^{\mathrm{T}}$ 为中心、半径为 $\alpha$ 的 KL 散度球 $U_\alpha(r,c)$。图中隐式假设最优传输解 $P^*$ 是唯一的。Sinkhorn 距离 $d_{M,\alpha}(r,c)$ 等于 $\langle P_\alpha, M \rangle$，即该散度球上与 $M$ 内积的最小值。当 $\alpha$ 足够大时，由于 $U_\alpha(r,c)$ 在 $P^*$ 附近逐渐与 $U(r,c)$ 重合，两个目标函数趋于一致。对偶 Sinkhorn 散度 $d_M^\lambda(r,c)$（即由负熵除以 $\lambda$ 正则化后的传输问题极值）在唯一解 $P^\lambda$ 处取得最小值，随着 $\lambda$ 的变化形成一条从 $r c^{\mathrm{T}}$ 到 $P^*$ 的正则化路径。对于给定的 $\alpha$ 值及一对 $(r,c)$，存在 $\lambda \in [0, \infty]$ 使得 $d_M^\lambda(r,c)$ 与 $d_{M,\alpha}(r,c)$ 重合。$d_M^\lambda$ 可以利用 Sinkhorn 的不动点迭代（1967）高效计算。尽管当 $\lambda \to \infty$ 时，该不动点迭代在理论上保证收敛至 $P^*$，但当超出依赖于具体问题的数值上限 $\lambda_{\max}$ 时，算法将无法正常工作，因为内存中 $e^{-\lambda M}$ 的部分元素会被表示为 0。

粘合引理（Gluing Lemma; Villani, 2009, p.19）是证明 OT 距离构成严格距离的关键。我们提出该引理的一个变体来证明我们的结论：

**引理 1（带有熵约束的粘合引理）**. *设 $\alpha \ge 0$ 且 $x, y, z \in \Sigma_d$。设 $P \in U_\alpha(x,y)$ 且 $Q \in U_\alpha(y,z)$。设 $S$ 为 $d \times d$ 矩阵，定义为 $s_{ik} := \sum_j \frac{p_{ij} q_{jk}}{y_j}$。则有 $S \in U_\alpha(x,z)$。*

证明见附录。我们可以采用与经典传输距离相同的证明策略来证明 $d_{M,\alpha}$ 的三角不等式：

*定理 1 的证明*. $d_{M,\alpha}$ 的对称性直接由 $M$ 的对称性导出。设 $x, y, z$ 为 $\Sigma_d$ 中的三个元素。设 $P \in U_\alpha(x,y)$ 与 $Q \in U_\alpha(y,z)$ 分别为 $d_{M,\alpha}(x,y)$ 与 $d_{M,\alpha}(y,z)$ 的最优解。利用引理 1 给出的 $U_\alpha(x,z)$ 中的矩阵 $S$，可展开如下不等式链：

$$
d_{M,\alpha}(x,z) = \min_{P \in U_\alpha(x,z)} \langle P, M \rangle \le \langle S, M \rangle = \sum_{ik} m_{ik} \sum_j \frac{p_{ij} q_{jk}}{y_j} \le \sum_{ijk} (m_{ij} + m_{jk}) \frac{p_{ij} q_{jk}}{y_j}
$$

$$
= \sum_{ijk} m_{ij} \frac{p_{ij} q_{jk}}{y_j} + m_{jk} \frac{p_{ij} q_{jk}}{y_j} = \sum_{ij} m_{ij} p_{ij} \sum_k \frac{q_{jk}}{y_j} + \sum_{jk} m_{jk} q_{jk} \sum_i \frac{p_{ij}}{y_j}
$$

$$
= \sum_{ij} m_{ij} p_{ij} + \sum_{jk} m_{jk} q_{jk} = d_{M,\alpha}(x,y) + d_{M,\alpha}(y,z). \quad \blacksquare
$$

---

### 4 利用 Sinkhorn 算法计算正则化传输

本节考虑 Sinkhorn 距离中熵约束的拉格朗日乘子：

$$
\text{对于 } \lambda > 0, \quad d_M^\lambda(r,c) := \langle P^\lambda, M \rangle, \quad \text{其中 } P^\lambda = \operatorname*{argmin}_{P \in U(r,c)} \langle P, M \rangle - \frac{1}{\lambda} h(P) \tag{2}
$$

由对偶理论可知，对每个 $\alpha$，均存在一个 $\lambda \in [0, \infty]$ 使得对该特定分布对 $(r,c)$ 成立 $d_{M,\alpha}(r,c) = d_M^\lambda(r,c)$。我们将 $d_M^\lambda$ 称为*对偶 Sinkhorn 散度*（Dual-Sinkhorn Divergence），并表明其计算成本远低于原始距离 $d_M$。

图 1 总结了 $d_M, d_{M,\alpha}$ 和 $d_M^\lambda$ 之间的关系。由于 $P^\lambda$ 的熵随 $\lambda$ 单调递减，计算 $d_{M,\alpha}$ 可以通过不断增大 $\lambda$ 的值计算 $d_M^\lambda$，直至 $h(P^\lambda)$ 达到 $h(r) + h(c) - \alpha$。本文暂不考虑此问题，仅在实验中使用对偶 Sinkhorn 散度。

#### 利用矩阵缩放算法计算 $d_M^\lambda$

给最优传输问题添加熵正则化强制赋予了最优正则化传输矩阵 $P^\lambda$ 一个简单的结构：

**引理 2**. *对于 $\lambda > 0$，解 $P^\lambda$ 是唯一的，且具有如下形式：*

$$
P^\lambda = \operatorname{diag}(u) K \operatorname{diag}(v)
$$

*其中 $u$ 和 $v$ 是 $\mathbb{R}^d$ 中在相差一个乘性常数的意义下唯一确定的非负向量，$K := e^{-\lambda M}$ 是 $-\lambda M$ 按元素作用的指数矩阵。*

*证明*. $P^\lambda$ 的存在性与唯一性源于 $U(r,c)$ 的有界性以及负熵函数的严格凸性。$P^\lambda$ 可以写为 $K$ 的重缩放形式是传输理论中的已知事实（Erlander and Stewart, 1990, §3.3）：记公式 (2) 对应 $U(r,c)$ 中两个等式约束的拉格朗日函数为 $\mathcal{L}(P, \alpha, \beta)$（其中对偶变量 $\alpha, \beta \in \mathbb{R}^d$）：

$$
\mathcal{L}(P, \alpha, \beta) = \sum_{ij} \frac{1}{\lambda} p_{ij} \log p_{ij} + p_{ij} m_{ij} + \alpha^{\mathrm{T}} (P \mathbf{1}_d - r) + \beta^{\mathrm{T}} (P^{\mathrm{T}} \mathbf{1}_d - c)
$$

对任意指标对 $(i,j)$，令 $\partial \mathcal{L} / \partial p_{ij} = 0 \implies p_{ij} = e^{-1/2 - \lambda \alpha_i} e^{-\lambda m_{ij}} e^{-1/2 - \lambda \beta_j}$。由于 $K$ 严格正，Sinkhorn 定理（1967）指出存在*唯一*形式为 $\operatorname{diag}(u) K \operatorname{diag}(v)$ 的矩阵属于 $U(r,c)$，其中 $u, v \ge \mathbf{0}_d$。因此 $P^\lambda$ 必然为该矩阵，且可通过 Sinkhorn 不动点迭代 $(u,v) \leftarrow (r ./ K v, c ./ K^{\mathrm{T}} u)$ 求得。$\blacksquare$

给定 $K$ 以及边际分布 $r$ 和 $c$，只需迭代 Sinkhorn 更新足够的次数即可收敛到 $P^\lambda$。可以证明，这些连续更新在 KL 散度意义下迭代地执行了 $K$ 在 $U(r,c)$ 上的投影。该不动点迭代可以写为单步更新 $u \leftarrow r ./ K (c ./ K^{\mathrm{T}} u)$。当 $r > \mathbf{0}_d$ 时，可将 $\operatorname{diag}(1./r) K$ 预先存储在 $d \times d$ 矩阵 $\tilde{K}$ 中，从而在更新 $u \leftarrow 1./(\tilde{K} (c ./ K^{\mathrm{T}} u))$ 时节省一次 Schur 向量积运算。如算法 1 第一行所示，通过选取 $r$ 的正元素索引可以轻松确保这一点。

---

#### 算法 1：计算 $\mathbf{d} = [d_M^\lambda(r, c_1), \dots, d_M^\lambda(r, c_N)]$（Matlab 语法）

```matlab
% 输入: M, lambda, r, C := [c_1, ..., c_N]
I = (r > 0); r = r(I); M = M(I, :); K = exp(-lambda * M);
u = ones(length(r), N) / length(r);
K_tilde = bsxfun(@rdivide, K, r); % 等价于 K_tilde = diag(1./r) * K

while u 发生变化或满足其他终止条件
    u = 1. ./ (K_tilde * (C ./ (K' * u)));
end

v = C ./ (K' * u);
d = sum(u .* ((K .* M) * v));
```

---

#### 并行性、收敛性与终止条件

正如上文所示，Sinkhorn 算法可以被向量化并推广到 $N$ 个目标直方图 $c_1, \dots, c_N$ 的情形。当 $N = 1$ 且算法 1 中的 $C$ 为向量时，退化为引理 2 证明中提到的简单迭代。当 $N > 1$ 时，可以通过更新单个缩放因子矩阵 $u \in \mathbb{R}_+^{d \times N}$（而非更新缩放向量 $u \in \mathbb{R}_+^d$）来*同时*完成 $N$ 个目标直方图的计算。这一关键特性使得算法 1 的执行极度适合 GPGPU 架构。尽管该领域一直在深入研究（Bieling et al., 2010），但在网络单纯形等复杂迭代求解器上尚未取得此类加速效果。利用 Hilbert 投影度量，Franklin 和 Lorenz（1989）证明了缩放因子 $u$（以及 $v$）的收敛性是线性的，其收敛速率上界为 $\kappa(K)^2$，其中：

$$
\kappa(K) = \frac{\sqrt{\theta(K)} - 1}{\sqrt{\theta(K)} + 1} < 1, \quad \text{且 } \theta(K) = \max_{i,j,l,m} \frac{K_{il} K_{jm}}{K_{jl} K_{im}}
$$

收敛速率上界 $\kappa(K)$ 随 $\lambda$ 的增大而趋近于 1；我们确实观察到，随着 $P^\lambda$ 逐渐逼近最优顶点 $P^*$（或当解不唯一时逼近 $U(r,c)$ 的最优面），收敛速度会变慢。算法 1 可以采用不同的终止条件，本文考虑了两种具体的终止策略。


### 5 实验结果

#### MNIST 手写数字数据集

我们在 MNIST 手写数字数据集上测试了对偶 Sinkhorn 散度的性能。每张图像均转换为 $20 \times 20$ 像素网格上的灰度强度向量，并归一化使其和为 1。我们在数据集中选取大小为 $N \in \{3, 5, 12, 17, 25\} \times 10^3$ 的子集。对于每个子集，我们采用重复 6 次的 4 折交叉验证（CV，3 折测试，1 折训练）方案，共进行 24 次独立实验，报告分类误差的均值与标准差。给定距离 $d$，我们构建核函数 $e^{-d/t}$，其中 $t > 0$ 在每个训练折中通过 CV 从集合 $\{1, q_{10}(d), q_{20}(d), q_{50}(d)\}$ 中选取（$q_s$ 表示该折中所观察到的距离子集的 $s\%$ 分位数）。对于计算得到的非正定核矩阵，我们通过添加足够大的对角项进行正则化。使用 Libsvm（采用一对一策略）进行多分类 SVM 训练。正则化参数 $C$ 在训练折上通过 2 折/2 次重复的 CV 从 $10^{\{-2, 0, 4\}}$ 中选择。对比的距离包括：Hellinger 距离、$\chi^2$ 距离、全变差（Total Variation）以及平方欧氏距离（高斯核）。$M$ 为网格中 $20 \times 20$ 个箱（bin）之间的 $400 \times 400$ 维欧氏距离矩阵。在该示例中，我们还尝试了基于 $\exp(-t M.^2)$（$t>0$）及其逆的马氏距离（Mahalanobis distances），但不同 $t$ 取值下的结果均不具竞争力。对于独立核，我们考虑 $[m_{ij}^a]$，其中 $a \in \{0.01, 0.1, 1\}$ 在每个训练折上通过 CV 选取。我们将 $\lambda$ 选自：

$$
\{5, 7, 9, 11\} \times \frac{1}{q_{50}(M)}
$$

其中 $q_{50}(M(:))$ 为像素间距离的中位数。我们将不动点迭代次数固定为 20 次。在绝大多数（尽管并非全部）折中，$\lambda = 9$ 均为最优设定。对偶 Sinkhorn 散度以明显的优势超越了所有其他距离指标，包括在此标记为 EMD 的经典最优传输距离。

---

![图 2 MNIST 平均测试误差](figures/sinkhorn-distances/fig2.png)

> **图 2**：带阴影置信区间的平均测试误差。误差基于 1/4 数据集用于训练、3/4 用于测试计算得出，并在 4 折 $\times$ 6 次重复 = 24 次实验中取平均。

---

#### 对偶 Sinkhorn 散度是否收敛于 EMD？

我们研究了随着 $\lambda$ 的增大，对偶 Sinkhorn 散度向经典最优传输距离收敛的情况。由于公式 (2) 中的正则化项，$d_M^\lambda(r, c)$ 必然大于 $d_M(r, c)$，我们期望随着 $\lambda$ 的增大，这一差距逐渐缩小。图 3 绘制了从 MNIST 数据库中抽取的 $40^2$ 对图像上计算得到的相对偏差分布箱线图：

$$
\frac{d_M^\lambda(r, c) - d_M(r, c)}{d_M(r, c)}
$$

当 $\lambda > 50$ 时，$d_M^\lambda$ 通常能以极高的精度逼近 EMD（在 $\lambda = 50$ 和 $100$ 时，相对误差中位数分别为 $3.4\%$ 和 $1.2\%$）。在本实验以及*以下所有其他实验*中，我们在每次迭代中计算包含 $N$ 个散度值的向量 $\mathbf{d}$，并在 $N$ 个散度值的绝对变化率*均*小于万分之一时终止迭代，即满足如下判据时停止：

$$
\|\mathbf{d}_t ./ \mathbf{d}_{t-1} - \mathbf{1}\|_\infty < 10^{-4}
$$

---

![图 3 对偶 Sinkhorn 与 EMD 的差距](figures/sinkhorn-distances/fig3.png)

> **图 3**：在 MNIST 数据集子集上，对偶 Sinkhorn 散度与 EMD 之间的差距随 $\lambda$ 增大的衰减趋势。

---

#### 计算速度提升数个数量级

我们利用 Rubner 等人（1997）以及 Pele 和 Werman（2009）公开的代码实现，对比了经典最优传输距离与对偶 Sinkhorn 散度的计算速度。我们通过生成一个包含 $d$ 个顶点的随机图来构建随机距离矩阵 $M$（边存在概率为 $1/2$，边权在 0 到 1 之间均匀分布）。$M$ 是通过 Floyd-Warshall 算法（Ahuja et al., 1993, §5.6）从该连通矩阵计算得到的所有点对间最短路径矩阵。通过这种方法，$M$ 大概率是距离锥 $\mathcal{M}$ 的一条极射线（Avis, 1980, p.138）。随后将 $M$ 中的元素归一化使其具有单位中位数。我们在 MATLAB 中实现了算法 1，并调用了 `emd_mex` 和 `emd_hat_gd_metric` 等 MEX/C 模块。EMD 距离以及 Sinkhorn CPU 版本均在单核处理器（2.66 GHz Xeon）上运行，Sinkhorn GPU 版本在 NVIDIA Quadro K5000 显卡上运行。我们评估了 $\lambda \in \{1, 10, 50\}$ 的情形：$\lambda = 1$ 时 $K$ 矩阵相对密集，其结果与独立核相当；而在 $\lambda = 10$ 或 $50$ 时，$K = e^{-\lambda M}$ 包含极小的值。Rubner 等人的实现在直方图维度超过 $d = 512$ 时便无法运行。正如预期的那样，对偶 Sinkhorn 散度相比于 EMD 求解器的竞争优势随维度增长而愈发显著。利用 GPU 加速可以带来额外一个数量级的速度提升。

---

![图 4 计算时间随维度变化](figures/sinkhorn-distances/fig4.png)

> **图 4**：在 $d$ 维单形上均匀采样的两个直方图之间，计算距离所需的平均计算时间随 $d$ 变化的双对数图（log-log scale）。对偶 Sinkhorn 散度分别在单核 CPU 与 GPU 上运行。

---

#### 经验复杂度

为了准确刻画算法的实际开销，我们重复了上述实验，但重点关注计算给定点 $r$ 到单形上均匀采样的 $N$ 个直方图的散度集收敛时所需的典型迭代次数（即矩阵-矩阵乘法次数）。如图 5 所示，随着 $e^{-\lambda M}$ 逐渐呈现对角占优，向量 $\mathbf{d}$ 达到收敛所需的迭代次数有所增加。然而，总迭代次数似乎并不随维度 $d$ 的变化而变化。这一观察结果解释了为什么在上述图 4 中，算法随维度 $d$ 表现出二次（经验）时间复杂度：

$$
O(d^2)
$$

这些结果表明，实时跟踪实际逼近误差（即监控 $\mathbf{d}$ 的变化）这一昂贵操作并不是必需的，直接预设固定的迭代次数即可良好运行，并能获得更进一步的加速。

---

![图 5 收敛迭代次数](figures/sinkhorn-distances/fig5.png)

> **图 5**：在单形上均匀采样的直方图上，$\lambda$ 对算法收敛所需迭代次数的影响（双对数坐标系）。

### 6 结论

我们表明，使用熵惩罚对最优传输问题进行正则化，为计算 OT 开辟了全新的数值求解途径。这种正则化带来的加速效果*与对基础度量矩阵 $M$ 的任何假设均无关*。初步实验证据表明，对偶 Sinkhorn 散度的表现并不逊色于 EMD，在实际应用中甚至可能表现得更好。对偶 Sinkhorn 散度由正则化权重 $\lambda$ 进行参数化，调优时应兼顾计算效率与算法性能；但在实验中我们尚未发现需要在两者之间进行权衡取舍——事实上，适度较小的 $\lambda$ 取值似乎比较大的取值表现更佳。

#### 致谢

作者特别感谢：Zaid Harchaoui 建议了本文的题目，并指出了 $P$ 的互信息与其到 $r c^{\mathrm{T}}$ 的 KL 散度之间的联系；感谢 Lieven Vandenberghe、Philip Knight、Sanjeev Arora、Alexandre d’Aspremont 以及甘利俊一（Shun-Ichi Amari）富有成效的讨论；感谢匿名审稿人的宝贵意见。

---

### 7 附录：定理证明

*性质 2 的证明*. 集合 $U_0(r, c)$（原文记为 $U_1$）包含了所有满足 $h(P) = h(r) + h(c)$ 的联合概率分布 $P$。在此情形下，由定理（Cover and Thomas, 1991, Theorem 2.6.6）可知，$U_0(r, c)$ 只能为单元素集合 $\{r c^{\mathrm{T}}\}$。若 $M$ 为负定距离矩阵，则由（Berg et al., 1984, §3.3.2）可知，在某个欧氏空间 $\mathbb{R}^n$ 中存在向量组 $(\varphi_1, \dots, \varphi_d)$ 使得 $m_{ij} = \|\varphi_i - \varphi_j\|_2^2$。因此我们有：

$$
r^{\mathrm{T}} M c = \sum_{ij} r_i c_j \|\varphi_i - \varphi_j\|^2 = \left( \sum_i r_i \|\varphi_i\|^2 + \sum_j c_j \|\varphi_j\|^2 \right) - 2 \sum_{ij} \langle r_i \varphi_i, c_j \varphi_j \rangle
$$

$$
= r^{\mathrm{T}} u + c^{\mathrm{T}} u - 2 r^{\mathrm{T}} K c
$$

其中 $u_i = \|\varphi_i\|^2$ 且 $K_{ij} = \langle \varphi_i, \varphi_j \rangle$。从第一个等式推导至第二个等式用到了 $\sum_i r_i = \sum_j c_j = 1$ 的性质。$r^{\mathrm{T}} M c$ 是一个负定（negative definite, n.d.）核，因为它由两个负定核相加而成：第一项 $(r^{\mathrm{T}} u + c^{\mathrm{T}} u)$ 是同一个函数分别在 $r$ 与 $c$ 处取值的和，因而是负定核（Berg et al., 1984, §3.2.10）；后一项 $-2 r^{\mathrm{T}} K c$ 作为正定核的相反数，亦为负定核（Berg et al., 1984, Definition §3.1.1）。$\blacksquare$

**注**：上述证明提供了一种更快计算独立核的方法。给定矩阵 $M$，可以预先计算范数向量 $u$ 以及上述矩阵 $K$ 的 Cholesky 分解因子 $L$，从而通过对每个样本直方图 $r_i$ 左乘 $L$ 进行预处理，仅需存储 $L r_i$ 并预计算对角项 $r_i^{\mathrm{T}} u$。需要注意的是，独立核在具有相同 1-范数的直方图上是正定的，但对任意向量不再保证正定。

---

*引理 1 的证明*. 设 $T$ 为 $\{1, \dots, d\}^3$ 上的概率分布，对所有使得 $y_j > 0$ 的指标 $j$，其元素定义为：

$$
t_{ijk} := \frac{p_{ij} q_{jk}}{y_j} \tag{3}
$$

对满足 $y_j = 0$ 的指标 $j$，所有 $t_{ijk}$ 均设为 0。

定义 $S := [\sum_j t_{ijk}]_{ik}$。易见 $S$ 为 $x$ 与 $z$ 之间的传输矩阵。事实上：

$$
\sum_i \sum_j t_{ijk} = \sum_j \sum_i \frac{p_{ij} q_{jk}}{y_j} = \sum_j \frac{q_{jk}}{y_j} \sum_i p_{ij} = \sum_j \frac{q_{jk}}{y_j} y_j = \sum_j q_{jk} = z_k \quad (\text{列和})
$$

$$
\sum_k \sum_j t_{ijk} = \sum_j \sum_k \frac{p_{ij} q_{jk}}{y_j} = \sum_j \frac{p_{ij}}{y_j} \sum_k q_{jk} = \sum_j \frac{p_{ij}}{y_j} y_j = \sum_j p_{ij} = x_i \quad (\text{行和})
$$

下面证明 $h(S) \ge h(x) + h(z) - \alpha$。设 $(X, Y, Z)$ 为服从联合分布 $T$ 的三个随机变量。由公式 (3) 中 $T$ 的定义可知：

$$
p(X, Y, Z) = \frac{p(X, Y) p(Y, Z)}{p(Y)} = p(X) p(Y \mid X) p(Z \mid Y)
$$

因此三元组 $(X, Y, Z)$ 构成马尔可夫链 $X \to Y \to Z$（Cover and Thomas, 1991, 式 2.118）。由数据处理不等式（Data Processing Inequality; Cover and Thomas, 1991, 定理 2.8.1），下述互信息不等式成立：

$$
I(X; Y) \ge I(X; Z)
$$

即：

$$
h(X, Z) - h(X) - h(Z) \ge h(X, Y) - h(X) - h(Y) \ge -\alpha
$$

由此得证。$\blacksquare$

---

### 参考文献 (References)

* Ahuja, R., Magnanti, T., and Orlin, J. (1993). *Network Flows: Theory, Algorithms and Applications*. Prentice Hall.
* Avis, D. (1980). On the extreme rays of the metric cone. *Canadian Journal of Mathematics*, 32(1):126–144.
* Berg, C., Christensen, J., and Ressel, P. (1984). *Harmonic Analysis on Semigroups*. Number 100 in Graduate Texts in Mathematics. Springer Verlag.
* Bieling, J., Peschlow, P., and Martini, P. (2010). An efficient GPU implementation of the revised simplex method. In *Parallel Distributed Processing, 2010 IEEE International Symposium on*, pages 1–8.
* Brickell, J., Dhillon, I., Sra, S., and Tropp, J. (2008). The metric nearness problem. *SIAM J. Matrix Anal. Appl*, 30(1):375–396.
* Brualdi, R. A. (2006). *Combinatorial matrix classes*, volume 108. Cambridge University Press.
* Cover, T. and Thomas, J. (1991). *Elements of Information Theory*. Wiley & Sons.
* Darroch, J. N. and Ratcliff, D. (1972). Generalized iterative scaling for log-linear models. *The Annals of Mathematical Statistics*, 43(5):1470–1480.
* Erlander, S. and Stewart, N. (1990). *The gravity model in transportation analysis: theory and extensions*. Vsp.
* Ferradans, S., Papadakis, N., Rabin, J., Peyré, G., Aujol, J.-F., et al. (2013). Regularized discrete optimal transport. In *International Conference on Scale Space and Variational Methods in Computer Vision*, pages 1–12.
* Franklin, J. and Lorenz, J. (1989). On the scaling of multidimensional matrices. *Linear Algebra and its applications*, 114:717–735.
* Good, I. (1963). Maximum entropy for hypothesis formulation, especially for multidimensional contingency tables. *The Annals of Mathematical Statistics*, pages 911–934.
* Grauman, K. and Darrell, T. (2004). Fast contour matching using approximate earth mover’s distance. In *IEEE Conf. Vision and Patt. Recog.*, pages 220–227.
* Gudmundsson, J., Klein, O., Knauer, C., and Smid, M. (2007). Small manhattan networks and algorithmic applications for the earth movers distance. In *Proceedings of the 23rd European Workshop on Computational Geometry*, pages 174–177.
* Indyk, P. and Thaper, N. (2003). Fast image retrieval via embeddings. In *3rd International Workshop on Statistical and Computational Theories of Vision (at ICCV)*.
* Jaynes, E. T. (1957). Information theory and statistical mechanics. *Phys. Rev.*, 106:620–630.
* Knight, P. A. (2008). The Sinkhorn-Knopp algorithm: convergence and applications. *SIAM Journal on Matrix Analysis and Applications*, 30(1):261–275.
* Ling, H. and Okada, K. (2007). An efficient earth mover’s distance algorithm for robust histogram comparison. *IEEE Transactions on Patt. An. and Mach. Intell.*, pages 840–853.
* Naor, A. and Schechtman, G. (2007). Planar earthmover is not in $l_1$. *SIAM J. Comput.*, 37(3):804–826.
* Pele, O. and Werman, M. (2009). Fast and robust earth mover’s distances. In *ICCV'09*.
* Rubner, Y., Guibas, L., and Tomasi, C. (1997). The earth movers distance, multi-dimensional scaling, and color-based image retrieval. In *Proceedings of the ARPA Image Understanding Workshop*, pages 661–668.
* Shirdhonkar, S. and Jacobs, D. (2008). Approximate earth movers distance in linear time. In *CVPR 2008*, pages 1–8. IEEE.
* Sinkhorn, R. (1967). Diagonal equivalence to matrices with prescribed row and column sums. *The American Mathematical Monthly*, 74(4):402–405.
* Villani, C. (2009). *Optimal transport: old and new*, volume 338. Springer Verlag.
* Wilson, A. G. (1969). The use of entropy maximising models, in the theory of trip distribution, mode split and route split. *Journal of Transport Economics and Policy*, pages 108–126.