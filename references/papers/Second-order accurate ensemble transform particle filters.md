### **二阶精度集合变换粒子滤波器**

**作者：** Walter Acevedo\*，Jana de Wiljes†，Sebastian Reich‡
**日期：** 2017年4月11日

---

#### **摘要**

粒子滤波（亦称序贯蒙特卡洛方法）被广泛应用于非线性演化方程背景下的状态和参数估计问题。最近提出的集合变换粒子滤波（ETPF）（S. Reich, *A non-parametric ensemble transform method for Bayesian inference*, SIAM J. Sci. Comput., 35, (2013), pp. A2013–A2014）用线性变换替代了标准粒子滤波中的重采样步骤，这使得粒子滤波与集合卡尔曼滤波的结合（混合化）成为可能，并使得到的混合滤波器能够适用于空间扩展系统。

然而，该线性变换步骤计算量大，且在中小规模集合样本下会导致对集合离散度（ensemble spread）的低估。在本文中，我们通过开发 ETPF 的二阶精度扩展方法，同时解决了这两个缺陷。这些扩展方法尤其允许人们使用 Sinkhorn 近似来替代线性输运（传输）问题的精确解。我们还证明了非线性集合变换滤波（NETF）是我们这一通用框架下的一个特例。

我们通过混沌 Lorenz-63 和 Lorenz-96 模型以及一个动态场景注视（scene-viewing）模型展示了二阶精度滤波器的性能。Lorenz-63 和 Lorenz-96 模型的数值结果表明，在中小规模集合样本下，与标准集合卡尔曼滤波和 ETPF 相比，该方法能实现显著的精度提升。另一方面，场景注视模型的数值结果表明，二阶修正可能会导致从后验参数分布中采出的样本出现统计不一致性。

---

**关键词：** 贝叶斯推断（Bayesian inference），数据同化（data assimilation），粒子滤波（particle filter），集合卡尔曼滤波（ensemble Kalman filter），Sinkhorn 近似（Sinkhorn approximation）

**AMS(MOS) 主题分类：** 65C05, 62M20, 93E11, 62F15, 86A22

### **1 引言 (Introduction)**

数据同化（Data assimilation, DA）是指将演化模型与底层动力学过程的部分观测数据相结合的广泛研究领域 [10, 15, 22]。数据同化算法主要表现为变分方法和/或基于集合的方法 [15]。在本文中，我们重点关注基于集合的 DA 方法及其稳健且高效的实现。集合卡尔曼滤波（EnKF）[10] 是迄今为止最流行的基于集合的 DA 方法，并在地球科学领域得到了广泛应用。然而，对于部分可观测的非线性过程，EnKF 会导致不一致的近似（inconsistent approximations）。相反，粒子滤波（PF，亦称序贯蒙特卡洛方法）[8] 能够产生一致的近似，但为了追踪底层的参考过程，通常需要比 EnKF 大得多的集合规模（粒子数）[2]。

为了克服这些缺点，当前出现了一种明显的趋势，即开发结合 EnKF 与 PF 的混合滤波器（hybrid filters），这类滤波器适用于中小集合规模下的强非线性系统。这里提及的代表性方法包括：高斯混合滤波（例如文献 [24]）、秩直方图滤波（rank histogram filter）[1, 19]、矩匹配集合滤波（moment matching ensemble filters）[28, 16, 25]、集合卡尔曼粒子滤波 [11] 以及混合集合变换粒子滤波 [6]。

在本文中，我们聚焦于集合变换粒子滤波（ETPF）[21, 22] 的改进实现及其与 EnKF 的混合化 [6]。ETPF 在每个同化步骤中都需要求解一个线性输运（传输）问题，这使得该方法的计算代价显著高于 EnKF。在计算上极具吸引力的替代方案（例如 Sinkhorn 近似 [7]）会导致实现不稳定，因为此时集合会出现欠离散（underdispersive，即离散度不足/过于集中）。我们通过引入 ETPF 的一种变体来解决此问题，该变体无论底层最优输运问题采用何种实际求解过程，均具备二阶精度。如果集合的后验均值和协方差矩阵与贝叶斯推断步骤中的重要性采样估计值一致，则称该集合滤波器具有**二阶精度**。二阶精度粒子滤波最早在文献 [28] 中被提出，此后人们又开发了多种变体 [16, 25]。在本文中，我们转而考虑对 ETPF 进行二阶修正。这种修正需要求解一个连续时间代数黎卡提方程（continuous-time algebraic Riccati equation）[27, 14]。当集合规模趋于无穷大时，该修正项趋近于零，这与 ETPF 的一致性是一致的 [21]。

本文结构安排如下：

* **第 2 节** 概述了集合变换滤波器的通用框架。
* **第 3 节** 总结了 ETPF 并引入了二阶修正步骤。
* **第 4 节**（原文标记为 Sectionsec:Riccati）讨论了相关连续时间代数黎卡提方程的数值求解过程。
* **第 5 节** 介绍了针对 ETPF 最优输运问题的 Sinkhorn 近似。
* **第 6 节** 总结了 ETPF 的整体二阶精度实现方案。
* **第 7 节** 给出了数值实验结果，在高度非线性和混沌的 Lorenz-63 [17] 与 Lorenz-96 [18] 模型上展示了新方法的性能。在此，我们复现了文献 [6] 中的实验，并将 ETPF 替换为基于最优输运 Sinkhorn 近似的二阶精度变体。最后，我们还展示了新滤波器在场景注视模型 *SceneWalk* [9] 参数估计中的表现。

---

#### **【脚注信息】**

* \* 德国波茨坦大学数学研究所（Karl-Liebknecht-Str. 24/25, D-14476 Potsdam, Germany）
* † 德国波茨坦大学数学研究所（Karl-Liebknecht-Str. 24/25, D-14476 Potsdam, Germany）
* ‡ 德国波茨坦大学数学研究所（sreich@math.uni-potsdam.de）及 英国雷丁大学数学与统计系（PO Box 220, Reading RG6 6AX, UK）

### **2 基于集合的预报-数据同化系统 (Ensemble-based forecasting-data assimilation systems)**

假设在时刻 $t_k$（$k = 1, \dots, K$）可以获取观测数据 $\mathbf{y}^{\text{obs}}(t_k) \in \mathbb{R}^{N_y}$，且这些观测数据通过似然函数与演化模型的状态变量 $\mathbf{z} \in \mathbb{R}^{N_z}$

$$
\mathbf{z}(t_k) = \mathcal{M}(\mathbf{z}(t_{k-1})) \tag{1}
$$

相关联，似然函数形式为：

$$
\pi(\mathbf{y}|\mathbf{z}) = \frac{1}{(2\pi)^{N_y/2}|\mathbf{R}|^{1/2}} \exp\left( -\frac{1}{2}(h(\mathbf{z}) - \mathbf{y})^{\text{T}} \mathbf{R}^{-1} (h(\mathbf{z}) - \mathbf{y}) \right), \tag{2}
$$

其中 $\mathbf{R} \in \mathbb{R}^{N_y \times N_y}$ 表示测量误差协方差矩阵。

一个基于集合的预报-数据同化（FOR-DA）系统在任意时刻 $t_k$ 都会生成两个规模为 $M$ 的集合。首先是预报集合（forecast ensemble）$\{\mathbf{z}_i^{\text{f}}\}_{i=1}^M$，用于近似条件分布 $\pi(\mathbf{z}, t_k | \mathbf{y}^{\text{obs}}_{1:k-1})$；其次是分析集合（analysis ensemble）$\{\mathbf{z}_i^{\text{a}}\}_{i=1}^M$，用于近似条件分布 $\pi(\mathbf{z}, t_k | \mathbf{y}^{\text{obs}}_{1:k})$。在此，

$$
\mathbf{y}^{\text{obs}}_{1:l} = (\mathbf{y}^{\text{obs}}(t_1), \mathbf{y}^{\text{obs}}(t_2), \dots, \mathbf{y}^{\text{obs}}(t_l)) \in \mathbb{R}^{N_y \times l} \tag{3}
$$

表示从 $t = t_1$ 到 $t = t_l$ 的全部观测数据集合。同时需注意：

$$
\mathbf{z}_i^{\text{f}}(t_k) = \mathcal{M}(\mathbf{z}_i^{\text{a}}(t_{k-1})) \tag{4}
$$

且不同的 FOR-DA 系统的主要区别在于所采用的数据同化算法。

本文所考虑的数据同化算法均具有**线性集合变换滤波（LETF）**[22] 的形式：

$$
\mathbf{z}_j^{\text{a}}(t_k) = \sum_{i=1}^M \mathbf{z}_i^{\text{f}}(t_k) d_{ij}(t_k) \tag{5}
$$

其中 $M \times M$ 变换矩阵 $\mathbf{D}(t_k) = \{d_{ij}(t_k)\}$ 的元素 $d_{ij}(t_k)$ 满足如下约束条件：对于所有 $j = 1, \dots, M$，

$$
\sum_{i=1}^M d_{ij}(t_k) = 1 \tag{6}
$$

换言之，在满足 $M \le N_z$ 的前提下，分析集合成员 $\mathbf{z}_j^{\text{a}}(t_k)$ 位于由预报集合 $\mathbf{z}_i^{\text{f}}(t_k)$（$i \in \{1,\dots,M\}$）所张成的 $(M-1)$ 维超平面内。需要注意的是，$\mathbf{D}$ 的元素可以为负值，参见文献 [22]。

具有 LETF 结构的一个著名经典 DA 算法族是 EnKF 算法族 [10, 22]。长期以来人们公认 EnKF 具有极强的鲁棒性，但其底层的高斯性和线性假设限制了它在更具一般性的系统中的适用性。为了克服以 EnKF 为代表的传统技术的不足，人们提出了其他适用于非线性模型场景、且应用于高维系统时计算可行的算法。例如，文献 [28, 25] 提出的非线性集合变换滤波（NETF）就提供了一个采用 LETF 形式的粒子滤波范例，它基于归一化重要性权重

$$
w_i(t_k) := \frac{\widehat{w}_i(t_k)}{\sum_{j=1}^M \widehat{w}_j(t_k)} \tag{7}
$$

（其中 $\widehat{w}_i(t_k) = \pi(\mathbf{y}(t_k)|\mathbf{z}_i^{\text{f}}(t_k))$），从而能够重现后验分布的一阶和二阶矩。

然而，本文的重点是 **ETPF**，它同样可以表述为式 (5) 的形式 [10, 22]，其中变换矩阵 $\mathbf{D}(t_k) = \{d_{ij}(t_k)\}$ 是通过最小化以下代价泛函定义的：

$$
J(\mathbf{D}(t_k)) = \sum_{i,j=1}^M d_{ij}(t_k) \|\mathbf{z}_i^{\text{f}}(t_k) - \mathbf{z}_j^{\text{f}}(t_k)\|^2 \tag{8}
$$

并满足约束条件 $d_{ij}(t_k) \ge 0$、式 (6) 以及

$$
\frac{1}{M}\sum_{j=1}^M d_{ij}(t_k) = w_i(t_k) \tag{9}
$$

[21]。ETPF 的核心思想是近似服从概率分布 $\pi_{Z^{\text{f}}}(\mathbf{z}, t_k)$ 的随机变量 $Z^{\text{f}}(t_k)$ 与对应于分布 $\pi_{Z^{\text{a}}}(\mathbf{z}, t_k)$ 的随机变量 $Z^{\text{a}}(t_k)$ 之间的转移映射（transfer map）。该映射诱导了各自概率密度之间的耦合，且这种耦合在最小化两个随机变量之间的期望距离意义上是最优的，即：

$$
\mu^*_Z = \arg\inf_{\mu \in \Pi(\pi_{Z^{\text{f}}}, \pi_{Z^{\text{a}}})} \sqrt{\mathbb{E}\|Z^{\text{f}}(t_k) - Z^{\text{a}}(t_k)\|^2}. \tag{10}
$$

直观上很明显，通过对式 (10) 的优化，预报随机变量与分析随机变量之间的相关性得到了增强，从而在先验与后验之间建立了强关联。由于我们仅依赖重要性权重，因此我们的滤波器也适用于非高斯似然函数。ETPF 还可以利用局域化（localization）思想 [5] 应用于空间扩展系统，并已在一种混合方法中与 EnKF 相结合 [6]。虽然在集合规模极限 $M \to \infty$ 下 ETPF 会收敛到真实的后验分布 [21]，但一般而言 EnKF 或 NETF 并不具备这种收敛性质。然而，ETPF 计算代价高昂，并且在有限集合规模下会低估集合离散度（协方差矩阵）（参见文献 [22] 中的例 8.11）。这两个缺陷都将在第 3 节和第 5 节提出的 LETF 中予以解决。

### **3 二阶精度线性集合变换滤波（Second-order accurate LETFs）**

现在我们推导二阶精度的 LETF。这里的二阶精度是指严格按照重要性采样方法精确重现一阶矩与二阶矩。

**定义 3.1** 若 LETF (5) 的分析均值满足

$$
\overline{\mathbf{z}}^{\text{a}}(t_k) = \frac{1}{M} \sum_{i=1}^M \mathbf{z}_i^{\text{a}}(t_k) = \sum_{i=1}^M w_i(t_k)\mathbf{z}_i^{\text{f}}(t_k) \tag{11}
$$

且分析协方差矩阵

$$
\widehat{\mathbf{P}}^{\text{a}}(t_k) = \frac{1}{M} \sum_{i=1}^M (\mathbf{z}_i^{\text{a}}(t_k) - \overline{\mathbf{z}}^{\text{a}}(t_k))(\mathbf{z}_i^{\text{a}}(t_k) - \overline{\mathbf{z}}^{\text{a}}(t_k))^{\text{T}} \tag{12}
$$

等于由重要性权重定义的协方差矩阵，即

$$
\mathbf{P}^{\text{a}}(t_k) = \sum_{i=1}^M w_i(t_k)(\mathbf{z}_i^{\text{f}}(t_k) - \overline{\mathbf{z}}^{\text{a}}(t_k))(\mathbf{z}_i^{\text{f}}(t_k) - \overline{\mathbf{z}}^{\text{a}}(t_k))^{\text{T}}, \tag{13}
$$

则称该 LETF 具有**二阶精度**。

---

**注 3.1** 在等权重 $w_i = 1/M$ 的情况下，通过重要性采样导出的协方差矩阵 (13) 其分母为 $M$。与此一致，本文采用了经验协方差 (12) 的有偏估计形式。另一种选择是在 (13) 中引入因子 $\frac{M}{M-1}$ 以获得无偏变体（例如 NETF 中所采用的形式，参见 [25]）。

由于在本节及后续各节中仅考虑 FOR-DA 系统的 DA 步骤，为简化符号表示，以下省去显式的时间依赖关系。我们引入预报集合的 $N_z \times M$ 矩阵

$$
\mathbf{Z}^{\text{f}} = (\mathbf{z}_1^{\text{f}}, \mathbf{z}_2^{\text{f}}, \dots, \mathbf{z}_M^{\text{f}}) \in \mathbb{R}^{N_z \times M} \tag{14}
$$

以及对应的分析集合矩阵

$$
\mathbf{Z}^{\text{a}} = (\mathbf{z}_1^{\text{a}}, \mathbf{z}_2^{\text{a}}, \dots, \mathbf{z}_M^{\text{a}}) \in \mathbb{R}^{N_z \times M}. \tag{15}
$$

此时，LETF (5) 可表示为矩阵形式：

$$
\mathbf{Z}^{\text{a}} = \mathbf{Z}^{\text{f}}\mathbf{D}. \tag{16}
$$

我们还引入全 1 向量 $\mathbf{1} = (1, 1, \dots, 1)^{\text{T}} \in \mathbb{R}^{M \times 1}$、由式 (7) 定义的归一化重要性权重向量

$$
\mathbf{w} = (w_1, \dots, w_M)^{\text{T}} \in \mathbb{R}^{M \times 1}, \tag{17}
$$

以及对角矩阵 $\mathbf{W} = \operatorname{diag}(\mathbf{w}) \in \mathbb{R}^{M \times M}$。由于分析均值由 (11) 给出，若满足

$$
\frac{1}{M}\mathbf{Z}^{\text{a}}\mathbf{1} = \mathbf{Z}^{\text{f}}\mathbf{w}, \tag{18}
$$

则该 LETF 具有一阶精度。若 $\mathbf{D}$ 满足式 (9)，即

$$
\frac{1}{M}\mathbf{D}\mathbf{1} = \mathbf{w}, \tag{19}
$$

则式 (18) 成立。回顾可知变换矩阵还需满足约束 (6)，其等价于 $\mathbf{D}^{\text{T}}\mathbf{1} = \mathbf{1}$ [22]。在下文中，我们将重点讨论由属于如下矩阵类的变换矩阵 $\mathbf{D}$ 所刻画的一阶精度 LETF：

$$
\mathcal{D}_1 = \{\mathbf{D} \in \mathbb{R}^{M \times M} \mid \mathbf{D}^{\text{T}}\mathbf{1} = \mathbf{1},\; \mathbf{D}\mathbf{1} = M\mathbf{w}\}. \tag{20}
$$

例如，这些条件可由以下变换矩阵满足：

$$
\mathbf{D}_0 = \mathbf{w}\mathbf{1}^{\text{T}}, \tag{21}
$$

此时对应的分析集合为

$$
\mathbf{Z}^{\text{a}} = \overline{\mathbf{z}}^{\text{a}}\mathbf{1}^{\text{T}}. \tag{22}
$$

---

**注 3.2** EnKF 也会导出形式为 (16) 的变换，其对应的 $\mathbf{D}_{\text{EnKF}}$ 满足 $\mathbf{D}_{\text{EnKF}}^{\text{T}}\mathbf{1} = \mathbf{1}$，但通常不满足式 (19) [22]。因此一般情况下 $\mathbf{D}_{\text{EnKF}} \notin \mathcal{D}_1$。通过简单的修正：

$$
\widehat{\mathbf{D}}_{\text{EnKF}} = \mathbf{D}_{\text{EnKF}}\left(\mathbf{I} - \frac{1}{M}\mathbf{1}\mathbf{1}^{\text{T}}\right) + \mathbf{D}_0 \tag{23}
$$

即可使 $\widehat{\mathbf{D}}_{\text{EnKF}} \in \mathcal{D}_1$。

---

注意，对于任意 $\mathbf{D} \in \mathcal{D}_1$，分析协方差矩阵 (12) 可以等价地写为：

$$
\widehat{\mathbf{P}}^{\text{a}} = \frac{1}{M}\mathbf{Z}^{\text{f}}(\mathbf{D} - \mathbf{w}\mathbf{1}^{\text{T}})(\mathbf{D} - \mathbf{w}\mathbf{1}^{\text{T}})^{\text{T}}(\mathbf{Z}^{\text{f}})^{\text{T}}. \tag{24}
$$

为达到二阶精度，式 (24) 必须等于后验协方差矩阵的重要性采样估计值 (13)，后者可表示为：

$$
\mathbf{P}^{\text{a}} = \mathbf{Z}^{\text{f}}(\mathbf{W} - \mathbf{w}\mathbf{w}^{\text{T}})(\mathbf{Z}^{\text{f}})^{\text{T}}. \tag{25}
$$

本文所考虑的二阶精度 LETF 类由如下集合刻画：

$$
\mathcal{D}_2 = \{\mathbf{D} \in \mathcal{D}_1 \mid (\mathbf{D} - \mathbf{w}\mathbf{1}^{\text{T}})(\mathbf{D} - \mathbf{w}\mathbf{1}^{\text{T}})^{\text{T}} = \mathbf{W} - \mathbf{w}\mathbf{w}^{\text{T}}\}. \tag{26}
$$

---

**注 3.3** 存在一个重要的子类 $\mathcal{D}_1^+ \subset \mathcal{D}_1$，它满足非负性约束 $d_{ij} \ge 0$，即：

$$
\mathcal{D}_1^+ = \{\mathbf{D} \in \mathcal{D}_1 \mid \text{对所有 } i, j = 1, \dots, M, \; d_{ij} \ge 0\}. \tag{27}
$$

此时 $\mathbf{D} \in \mathcal{D}_1^+$ 为左随机矩阵（left stochastic matrices），因而可解释为一种重采样方案：根据 $\mathbf{D}$ 的第 $j$ 列中的转移概率生成实现 $\mathbf{z}_j^{\text{a}}$（$j=1,\dots,M$）。然而，若确定性地使用此类随机矩阵生成分析集合（如 ETPF 中的做法），则粒子 $\mathbf{z}_j^{\text{a}}$ 将对应于 $\mathbf{D}$ 的第 $j$ 列所诱导随机变量的期望值。例如，考虑式 (21) 中的简单变换矩阵 $\mathbf{D}_0 \in \mathcal{D}_1^+$，此时对所有 $j \in \{1,\dots,M\}$ 均有 $\mathbf{z}_j^{\text{a}} = \overline{\mathbf{z}}^{\text{a}}$，所隐含的分析协方差矩阵 (24) 恒等于零，这显然是不可取的，且 $\mathbf{D}_0 \notin \mathcal{D}_2$。ETPF 的设计正是为了使这种效应最小化，并在 $M \to \infty$ 时渐近消失 [21, 22]。更广泛地说，在一般情况下有 $\mathcal{D}_1^+ \cap \mathcal{D}_2 = \emptyset$。

---

我们现在提出一种将变换矩阵 $\mathbf{D} \in \mathcal{D}_1$ 转化为变换矩阵 $\widehat{\mathbf{D}} \in \mathcal{D}_2$ 的通用方法。我们采用如下设定（ansatz）：

$$
\widehat{\mathbf{D}} = \mathbf{D} + \mathbf{\Delta} \tag{28}
$$

其中 $\mathbf{D} \in \mathcal{D}_1$，$\mathbf{\Delta} \in \mathbb{R}^{M \times M}$ 满足 $\mathbf{\Delta}\mathbf{1} = \mathbf{0}$、$\mathbf{\Delta}^{\text{T}}\mathbf{1} = \mathbf{0}$，且满足 $\mathbf{P}^{\text{a}} = \widehat{\mathbf{P}}^{\text{a}}$，其中

$$
\widehat{\mathbf{P}}^{\text{a}} = \frac{1}{M}\mathbf{Z}^{\text{f}}(\widehat{\mathbf{D}} - \mathbf{w}\mathbf{1}^{\text{T}})(\widehat{\mathbf{D}} - \mathbf{w}\mathbf{1}^{\text{T}})^{\text{T}}(\mathbf{Z}^{\text{f}})^{\text{T}}. \tag{29}
$$

条件

$$
\mathbf{0} = \mathbf{P}^{\text{a}} - \widehat{\mathbf{P}}^{\text{a}} = \mathbf{Z}^{\text{f}}\left\{ (\mathbf{W} - \mathbf{w}\mathbf{w}^{\text{T}}) - \frac{1}{M}(\widehat{\mathbf{D}} - \mathbf{w}\mathbf{1}^{\text{T}})(\widehat{\mathbf{D}} - \mathbf{w}\mathbf{1}^{\text{T}})^{\text{T}} \right\}(\mathbf{Z}^{\text{f}})^{\text{T}} \tag{30}
$$

与式 (28) 共同导出了关于修正项 $\mathbf{\Delta}$ 的二次方程：

$$
M(\mathbf{W} - \mathbf{w}\mathbf{w}^{\text{T}}) - (\mathbf{D} - \mathbf{w}\mathbf{1}^{\text{T}})(\mathbf{D} - \mathbf{w}\mathbf{1}^{\text{T}})^{\text{T}} = (\mathbf{D} - \mathbf{w}\mathbf{1}^{\text{T}})\mathbf{\Delta}^{\text{T}} + \mathbf{\Delta}(\mathbf{D} - \mathbf{w}\mathbf{1}^{\text{T}})^{\text{T}} + \mathbf{\Delta}\mathbf{\Delta}^{\text{T}}. \tag{31}
$$

若我们进一步选择 $\mathbf{\Delta}$ 为对称矩阵，则对于特例 (21)，式 (31) 简化为

$$
M(\mathbf{W} - \mathbf{w}\mathbf{w}^{\text{T}}) = \mathbf{\Delta}\mathbf{\Delta} \tag{32}
$$

此时式 (31) 的解可直接由对称平方根给出：

$$
\mathbf{\Delta} = \sqrt{M}(\mathbf{W} - \mathbf{w}\mathbf{w}^{\text{T}})^{1/2}, \tag{33}
$$

从而重现了 NETF [25, 28]。注意，当 $\mathbf{D} = \mathbf{w}\mathbf{1}^{\text{T}}$ 时，对于满足 $\mathbf{Q}\mathbf{1} = \mathbf{1}$ 的任意 $M \times M$ 正交矩阵 $\mathbf{Q}$，$\mathbf{\Delta}\mathbf{Q}$ 同样构成式 (31) 的解$^1$。下面的引理给出了如何以最优方式选取该正交矩阵 $\mathbf{Q}$。

---

**引理 3.1** 设 $\mathbf{\Delta}$ 为满足 (i) $\mathbf{\Delta}\mathbf{1} = \mathbf{0}$ 以及 (ii)

$$
\frac{1}{M}\mathbf{\Delta}\mathbf{\Delta}^{\text{T}} = \mathbf{W} - \mathbf{w}\mathbf{w}^{\text{T}} \tag{34}
$$

的任意 $M \times M$ 矩阵，并假设 $M \le N_z + 1$。定义 $M \times M$ 正交矩阵

$$
\mathbf{Q}_{\text{opt}} := \mathbf{U}_{\text{opt}}\mathbf{V}_{\text{opt}}^{\text{T}} \tag{35}
$$

其中两个 $M \times M$ 正交矩阵 $\mathbf{U}_{\text{opt}}$ 和 $\mathbf{V}_{\text{opt}}$ 由 $M \times M$ 矩阵

$$
\mathbf{S} = \mathbf{\Delta}(\widehat{\mathbf{Z}}^{\text{f}})^{\text{T}}\widehat{\mathbf{Z}}^{\text{f}}, \quad \widehat{\mathbf{Z}}^{\text{f}} := \mathbf{Z}^{\text{f}} - \frac{1}{M}\mathbf{Z}^{\text{f}}\mathbf{1}\mathbf{1}^{\text{T}} \tag{36}
$$

的奇异值分解（SVD）确定，即 $\mathbf{S} = \mathbf{U}_{\text{opt}}\mathbf{\Lambda}_{\text{opt}}\mathbf{V}_{\text{opt}}^{\text{T}}$。则变换矩阵

$$
\mathbf{D}_{\text{opt}} = \mathbf{w}\mathbf{1}^{\text{T}} + \mathbf{\Delta}\mathbf{Q}_{\text{opt}} \tag{37}
$$

将产生一个二阶精度的 LETF，它在所有二阶精度变换矩阵 $\mathbf{D} \in \mathcal{D}_2$ 中最小化：

$$
\widehat{J}(\mathbf{D}) = \frac{1}{M}\sum_{i=1}^M \|\mathbf{z}_i^{\text{a}} - \mathbf{z}_i^{\text{f}}\|^2. \tag{38}
$$

---

**证明：** 由于 $\widehat{\mathbf{Z}}^{\text{f}}\mathbf{1} = \mathbf{0}$，矩阵 $\mathbf{S}$ 除了满足 $\mathbf{S}^{\text{T}}\mathbf{1} = \mathbf{0}$ 外还满足 $\mathbf{S}\mathbf{1} = \mathbf{0}$，这表明 $\mathbf{Q}_{\text{opt}}\mathbf{1} = \mathbf{1}$，进而式 (37) 具有二阶精度。此外注意：

$$
\left(\mathbf{\Delta}(\widehat{\mathbf{Z}}^{\text{f}})^{\text{T}}\widehat{\mathbf{Z}}^{\text{f}}(\widehat{\mathbf{Z}}^{\text{f}})^{\text{T}}\widehat{\mathbf{Z}}^{\text{f}}\mathbf{\Delta}\right)^{-1/2}\mathbf{\Delta}(\widehat{\mathbf{Z}}^{\text{f}})^{\text{T}}\widehat{\mathbf{Z}}^{\text{f}} = (\mathbf{S}\mathbf{S}^{\text{T}})^{-1/2}\mathbf{S} \tag{39}
$$

$$
= (\mathbf{U}_{\text{opt}}\mathbf{\Lambda}_{\text{opt}}^{-1}\mathbf{U}_{\text{opt}}^{\text{T}})\mathbf{U}_{\text{opt}}\mathbf{\Lambda}_{\text{opt}}\mathbf{V}_{\text{opt}}^{\text{T}} \tag{40}
$$

文献 [20] 已经证明，在给定的预报均值、分析均值以及协方差矩阵下，该式能够最小化式 (38)，由此可得 $\mathbf{Q}_{\text{opt}} = \mathbf{U}_{\text{opt}}\mathbf{V}_{\text{opt}}^{\text{T}}$ 的最优性。另见文献 [22]。 $\blacksquare$

---

关于引理 3.1 中 $M \le N_z + 1$ 这一要求，需要补充两点说明：

1. 若样本数（集合规模）$M$ 超过状态空间维数 $N_z$，则在计算上更适宜采用如下形式来实现最优变换：

$$
\mathbf{z}_i^{\text{a}} = \overline{\mathbf{z}}^{\text{a}} + \mathbf{T}(\mathbf{z}_i^{\text{f}} - \overline{\mathbf{z}}^{\text{f}}), \tag{41}
$$

其中 $\mathbf{T} \in \mathbb{R}^{N_z \times N_z}$ 为适当定义的对称矩阵 [20, 22]。
2. 依然可以采用式 (35)，但应当将 $\mathbf{Q}_{\text{opt}}$ 右乘投影矩阵 $\mathbf{I} - \mathbf{1}\mathbf{1}^{\text{T}}/M$，以保证生成的变换矩阵 (37) 保持均值不变（mean preserving），即满足 $\mathbf{D}_{\text{opt}}\mathbf{1} = \mathbf{w}$。这一额外操作源于矩阵 $\mathbf{S}$ 此时将存在多个零奇异值。

---

**脚注：**
$^1$ 文献 [25] 中提出的 NETF 采用了满足 $\mathbf{Q}\mathbf{1} = \mathbf{1}$ 的随机正交矩阵，而文献 [28] 中的 NETF 则基于 $\mathbf{W} - \mathbf{w}\mathbf{w}^{\text{T}}$ 的非对称平方根。


### **4 连续时间代数黎卡提方程 (Continuous-time algebraic Riccati equation)**

现在我们回到一阶精度变换矩阵 $\mathbf{D}$ 的一般情形。此时，式 (31) 导出了关于对称修正项 $\mathbf{\Delta}$ 的连续时间代数黎卡提方程（CARE）。具体而言，引入：

$$
\mathbf{B} = \mathbf{D} - \mathbf{w}\mathbf{1}^{\text{T}}, \quad \mathbf{A} = M(\mathbf{W} - \mathbf{w}\mathbf{w}^{\text{T}}) - \mathbf{B}\mathbf{B}^{\text{T}} \tag{42}
$$

在假设 $\mathbf{\Delta}$ 为对称矩阵的前提下，方程 (31) 可表示为如下连续时间代数黎卡提方程：

$$
\mathbf{A} = \mathbf{B}\mathbf{\Delta} + \mathbf{\Delta}\mathbf{B}^{\text{T}} + \mathbf{\Delta}\mathbf{\Delta}. \tag{43}
$$

注意，式 (43) 可以看作动态黎卡提方程的稳态解：

$$
\frac{\text{d}}{\text{d}\tau}\mathbf{\Delta} = -\mathbf{B}\mathbf{\Delta} - \mathbf{\Delta}\mathbf{B}^{\text{T}} + \mathbf{A} - \mathbf{\Delta}\mathbf{\Delta}. \tag{44}
$$

由于方程 (44) 是可控的 [27]，初值条件为 $\mathbf{\Delta}(0) = \mathbf{0}$ 时，方程 (44) 的解 $\mathbf{\Delta}(\tau)$ 在 $\tau \to \infty$ 时将收敛至方程 (43) 的解 [4]。因此，采用显式欧拉法对式 (44) 进行足够多步的时间步进迭代，即可得到式 (43) 的近似解。本文后续展示的数值实验结果均采用了该方法。

---

**注 4.1** 或者，式 (43) 也可以通过文献 [14] 中的 Schur 向量法求解。Schur 向量法基于扩展哈密顿矩阵：

$$
\mathbf{H} = \begin{pmatrix} \mathbf{B}^{\text{T}} & \mathbf{I} \\ \mathbf{A} & -\mathbf{B} \end{pmatrix} \tag{45}
$$

及其上三角 Schur 分解：

$$
\mathbf{U}^{\text{T}}\mathbf{H}\mathbf{U} = \begin{pmatrix} \mathbf{S}_{11} & \mathbf{S}_{12} \\ \mathbf{0} & \mathbf{S}_{22} \end{pmatrix} \tag{46}
$$

其中 $\mathbf{S}_{11}$ 的谱实部均为负，$\mathbf{S}_{22}$ 的谱实部均为正。将正交矩阵 $\mathbf{U}$ 进行相应分块后，式 (31) 的解由下式给出：

$$
\mathbf{\Delta} = \mathbf{U}_{21}\mathbf{U}_{11}^{-1}. \tag{47}
$$

该计算方法要求矩阵对 $(\mathbf{A}^{1/2}, \mathbf{B})$ 是可检测的（detectable）[27, 14]。由于针对方程 (43) 这一条件并不总是得到满足，因此我们建议使用式 (44) 来求取方程 (43) 的近似解。此外，也可以利用文献 [12] 中讨论的更具一般性的拉格朗日不变子空间技术。

---

现在，我们既可以直接采用 ETPF 中的 $\mathbf{D}$ 来推导二阶精度的 ETPF，也可以先计算最优输运问题 (8) 的近似解 $\mathbf{D} \in \mathcal{D}_1^+$，再将其转化为二阶精度的粒子滤波。关于这一方面的详细内容将在第 5 节中展开讨论。

---

### **5 最优输运问题的 Sinkhorn 近似 (Sinkhorn approximation to the optimal transport problem)**

对于由代价泛函 (8) 以及 $\mathbf{D} \in \mathcal{D}_1^+$ 所定义的最优输运问题，其 Sinkhorn 近似由如下正则化代价泛函给出：

$$
\mathbf{D}_{\min}(\lambda) = \arg\min J_{\text{SH}}(\mathbf{D}) = \sum_{i,j=1}^M \left\{ d_{ij}\|\mathbf{z}_i^{\text{f}} - \mathbf{z}_j^{\text{f}}\|^2 + \frac{1}{\lambda} d_{ij} \ln \frac{d_{ij}}{d_{ij}^0} \right\} \tag{48}
$$

其中 $\lambda > 0$ 为正则化参数，$d_{ij}^0$ 为式 (21) 中定义的 $\mathbf{D}_0$ 的矩阵元。每个参数 $\lambda$ 都对应一个特定的 $\mathbf{D}_{\min}(\lambda) \in \mathcal{D}_1^+$，且 $\lambda \to \infty$ 时退化回原始代价函数 (8)。另一方面，当选取 $\lambda \to 0$ 时，式 (21) 成为其唯一极小值点。这是由于当 $d_{ij} = d_{ij}^0$ 时，式 (48) 中的正则化项取得极小值，即 $\lim_{\lambda \to 0}\mathbf{D}_{\min}(\lambda) = \mathbf{D}_0$。

---

**注 5.1** 在确定 $\mathbf{D}_{\min}(\lambda)$ 后，可以加上相应的二阶修正项 $\mathbf{\Delta}(\lambda)$。取决于 $\lambda$ 的取值，这将导出不同的二阶精度粒子滤波：例如 $\lambda \to 0$ 对应 NETF，而 $\lambda \to \infty$ 对应二阶修正后的 ETPF。换言之，调节 $\lambda$ 能够在 NETF 与二阶修正 ETPF 之间建立起自然的桥梁过渡。

---

求解式 (48) 的极小值点存在一种简明的迭代方法。首先注意到极小值点具有如下形式：

$$
\mathbf{D}_{\min}(\lambda) = \operatorname{diag}(\mathbf{u})\,\mathbf{K}\,\operatorname{diag}(\mathbf{v}) \tag{49}
$$

其中 $\mathbf{u} \in \mathbb{R}^{M \times 1}$ 与 $\mathbf{v} \in \mathbb{R}^{M \times 1}$ 为两个非负向量，矩阵 $\mathbf{K}$ 的元素为：

$$
k_{ij} = e^{-\lambda \|\mathbf{z}_i^{\text{f}} - \mathbf{z}_j^{\text{f}}\|^2}. \tag{50}
$$

未知向量 $\mathbf{u}$ 和 $\mathbf{v}$ 可通过 Sinkhorn 不动点迭代计算：

$$
\{M w_i / (\mathbf{K}\mathbf{v})_i\} \to \mathbf{u}, \quad \{1 / (\mathbf{Ku})_i\} \to \mathbf{v}. \tag{51}
$$

Sinkhorn 近似所需的计算复杂度为 $\mathcal{O}(M^2)$。高效实现方式及更多细节参见文献 [7]。

我们将 $\mathbf{u}$ 和 $\mathbf{v}$ 的迭代序列分别记为 $\mathbf{u}^l$ 与 $\mathbf{v}^l$，其中每次更新均先按式 (51) 左侧公式更新 $\mathbf{u}$。此时对应的矩阵：

$$
\mathbf{D}^l = \operatorname{diag}(\mathbf{u}^l)\,\mathbf{K}\,\operatorname{diag}(\mathbf{v}^l) \tag{52}
$$

满足 $(\mathbf{D}^l)^{\text{T}}\mathbf{1} = \mathbf{1}$，且权重向量：

$$
\mathbf{w}^l = \frac{1}{M}\mathbf{D}^l\mathbf{1} \tag{53}
$$

在 $l \to \infty$ 时收敛至 $\mathbf{w}$。若我们在迭代步数 $l_*$ 处终止迭代，则将对应的变换矩阵定义为：

$$
\mathbf{D} = \mathbf{D}^{l_*} - (\mathbf{w}^{l_*} - \mathbf{w})\mathbf{1}^{\text{T}}. \tag{54}
$$

迭代步数 $l_*$ 可由如下收敛条件确定：对于充分小的 $\varepsilon > 0$（例如 $\varepsilon = 10^{-8}$），满足

$$
\|\mathbf{w}^{l_*} - \mathbf{w}\| \le \varepsilon. \tag{55}
$$

---

### **6 算法总结 (Algorithmic summary)**

我们总结基于最优输运问题的 Sinkhorn 近似实现二阶精度 ETPF 的关键步骤。当然，Sinkhorn 近似也可以替换为任何现成的最优输运问题直接求解器。

假设已知预报集合成员矩阵 $\mathbf{Z}^{\text{f}}$ 与重要性权重向量 $\mathbf{w}$。算法执行以下步骤：

* **(i)** 选取最优输运 Sinkhorn 近似算法的正则化参数 $\lambda > 0$。根据式 (50) 计算矩阵 $\mathbf{K}$。对 $\mathbf{K}$ 的元素进行归一化，使其满足 $-\lambda^{-1}\ln k_{ij} \le 1$。根据更新公式 (51) 递推计算向量 $\mathbf{u}^l$ 和 $\mathbf{v}^l$，初始值设为 $\mathbf{v}^0 = \mathbf{1}$。持续迭代，直至变换矩阵 (52) 及其对应的权重向量 (53) 满足终止条件 (55)。注意在每次迭代中式 (52) 应满足 $\mathbf{1}^{\text{T}}\mathbf{D}^l = \mathbf{1}^{\text{T}}$。在我们的实验中设定容差 $\varepsilon = 10^{-8}$。最后通过式 (54) 计算得到变换矩阵 $\mathbf{D}$。
* **(ii)** 采用显式欧拉法求解动态黎卡提方程 (44) 以获得方程 (43) 关于修正项 $\mathbf{\Delta}$ 的解，步长设为 $\Delta \tau = 0.1$，初始条件设为 $\mathbf{\Delta}(0) = \mathbf{0}$。当满足如下条件时终止迭代：

$$
\|\mathbf{\Delta}((k+1)\Delta\tau) - \mathbf{\Delta}(k\Delta\tau)\|_\infty \le 10^{-3} \tag{56}
$$

并令 $\mathbf{\Delta} = \mathbf{\Delta}((k+1)\Delta\tau)$。

* **(iii)** 分析集合由下式给出：

$$
\mathbf{Z}^{\text{a}} = \mathbf{Z}^{\text{f}}\widehat{\mathbf{D}} = \mathbf{Z}^{\text{f}}(\mathbf{D} + \mathbf{\Delta}). \tag{57}
$$

---

需要指出的是，本文提出的二阶精度 ETPF 可以在文献 [6] 所述的混合滤波器中替代标准 ETPF；当应用于空间扩展系统时，亦可结合局域化（localization）技术使用。具体而言，混合滤波器基于将似然函数 (2) 分解为：

$$
\pi(\mathbf{y}|\mathbf{z}) = \pi(\mathbf{y}|\mathbf{z})^\alpha \times \pi(\mathbf{y}|\mathbf{z})^{1-\alpha} \tag{58}
$$

并对这两个因子分别应用不同的滤波器。另一方面，$R$-局域化方法会在计算区域的各个网格点 $x_k$ 处生成不同的变换矩阵 $\mathbf{D}(x_k)$。详细内容参见文献 [5, 22]。


### **8 结论 (Conclusions)**

我们提出并测试了 ETPF 的二阶变体。这些改进在计算上极具吸引力，因为它们允许人们利用 Sinkhorn 近似来替代计算代价高昂的最优输运问题精确解。此外，若将 Sinkhorn 近似中的正则化参数 $\lambda$ 设为零，且采用式 (35) 中最优选取的正交矩阵 $\mathbf{Q}_{\text{opt}}$，即可重现 NETF [25]；而 $\lambda \to \infty$ 则在形式上退化回 ETPF 基于最优输运的实现。作为副产物，我们还发现相较于文献 [25] 建议的随机选取方式，采用最优正交矩阵 $\mathbf{Q}$ 的 NETF 能够获得更小的均方根误差（RMSE）。

二阶精度 ETPF 可以无缝嵌入文献 [6] 的混合集合变换粒子滤波框架中；针对空间扩展演化方程（如 Lorenz-96 模型），亦可根据需要与局域化（localization）技术相结合 [10, 22, 5]。

Lorenz-63 和 Lorenz-96 模型的数值实验结果证实，本文提出的方法与文献 [6] 中的混合策略相结合，为序贯数据同化提供了一个极为强大的框架。值得一提的是，本文涉及的所有方法均可与替代提议分布密度（proposal densities）相结合，从而获得更为均衡的重要性权重 (7) [26]。

然而必须指出，实现二阶精度是有代价的——变换矩阵 $\widehat{\mathbf{D}}$ 的元素不再严格保证非负（这与原 ETPF 变换矩阵 $\mathbf{D}$ 的性质不同）。因此，分析集合并不必然包含在预报集合所张成的凸包（convex hull）之内。例如，当系统状态变量理论上仅允许在有界区间或半开区间内取值时，这可能会诱发非物理状态（non-physical states），正如在 *SceneWalk* 模型中所展示的那样。

---

### **致谢 (Acknowledgments)**

我们衷心感谢 Hans-Rudolf Künsch 与 Sylvain Robert 就线性集合变换滤波器的二阶修正展开的有益讨论。同时感谢 Ralf Engbert 与 Heiko Schütt 为第 7.3 节提供了研究所用的数据集。本项研究得到了德国科学基金会（DFG）通过合作研究中心 CRC 1114“复杂系统中的尺度级联”（*Scaling Cascades in Complex Systems*）项目 (A02)“大气流动的多尺度数据与渐近模型同化”（*Multiscale data and asymptotic model assimilation for atmospheric flows*）的部分资助。
