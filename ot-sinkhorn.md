输运设定 $Y = T(X) \Rightarrow T_* \mathbb{P}_X = T_*X_*\mathbb{P} = \mathbb{P}_Y$。

此时 Monge 的传输代价函数自然就是这对确定性绑定变量的数学期望：
$$
\int_{\mathcal{X}} c(x, T(x)) \, \mathrm{d}\mathbb{P}_X(x) = \mathbb{E}_{X \sim \mathbb{P}_X}[c(X, T(X))] = \mathbb{E}_{(X, Y) \sim \mathbb{P}_{(X, Y)}}[c(X, Y)]
$$
Monge 模型的局限在于其刚性绑定 $Y = T(X)$：在给定 $X=x$ 时，$Y$ 没有任何随机性，条件分布只能是单点脉冲 $\mathbb{P}_{Y \mid X=x} = \delta_{T(x)}$，导致每个源点 $x$ 无法将质量拆解分运至多个地点（亦即，$\mathbb{P}_{Y \mid X=x}$ 无法对应离散分布 $\sum_{j = 1}^{n} w_j \delta_{y_j}, n \geqslant 2$.）

松弛的核心操作即是解除函数绑定 $Y = T(X)$，允许 $(X, Y)$ 成为任意具备随机性的联合随机变量（即允许单点质量向多处分流），但仍然保留最初的两个边缘分布条件：
$$
(\pi_1)_* \mathbb{P}_{(X,Y)} = \mathbb{P}_X, (\pi_2)_* \mathbb{P}_{(X,Y)} = \mathbb{P}_Y
$$
由此，刚性（所谓刚性，反面是自由·流变·松弛·弹性）函数期望 $\mathbb{E}[c(X, T(X))]$ 瞬间拓展为在满足边际约束的联合分布测度上的全期望积分：
$$
\min_{\mathbb{P}_{(X,Y)} \in \Pi(\mathbb{P}_X, \mathbb{P}_Y)} \mathbb{E}_{(X,Y) \sim \mathbb{P}_{(X,Y)}}[c(X, Y)] = \min_{\mathbb{P}_{(X,Y)} \in \Pi(\mathbb{P}_X, \mathbb{P}_Y)} \int_{\mathcal{X} \times \mathcal{Y}} c(x, y) \, \mathrm{d}\mathbb{P}_{(X,Y)}(x, y)
$$

>  我的理解是，基本上，这只是将求解满足 $TX = Y$ 的输运映射 $T$，松弛为寻找边缘分布为 $X,Y$ 的联合分布 $\mathbb{P}_{(X,Y)}$。类似的思维联想有：隐函数定理或者拒绝采样问题。
最小化期望代价 $\mathbb{E}_{(X, Y) \sim \mathbb{P}_{(X, Y)}}[c(X, Y)]$ 则是需要求解的目标函数。

---
> 关于输运问题，我还想记录以下的推导。我认为这个推导对于理解后续内容是有帮助的。

设 $\mathbb{P}_X = \langle \bm{a}, \delta_{x_{1..m}} \rangle, \mathbb{P}_Y = \langle \bm{b}, \delta_{y_{1..n}} \rangle$，输运绑定 $Y = T(X)$ 使得条件转移核退化为脉冲 $\mathbb{P}_{Y \mid X=x} = \delta_{T(x)}$。离散目标测度 $\mathbb{P}_Y = \langle \bm{b}, \delta_{y_{1..n}} \rangle$ 在原子处的测度质量由期望给出为 $b_j = \mathbb{P}_Y(\{y_j\}) = \mathbb{E}_{Y\sim \mathbb{P}_Y}[\mathbb{I}_{\{y_j\}}(Y)]$，计算有
$$\begin{aligned}
& b_j = \mathbb{E}_{X\sim \mathbb{P}_X}[\mathbb{E}_{Y\mid X}[\mathbb{I}_{\{y_j\}}(Y)]] = \mathbb{E}_{X\sim \mathbb{P}_X}[\mathbb{I}_{\{y_j\}}(T(X))] \\
= & \int_{\mathcal{X}} \mathbb{I}_{\{y_j\}}(T(x))\,\mathrm{d}\Bigl(\sum_{i=1}^m a_i \delta_{x_i}\Bigr)(x) = \sum_{i=1}^m a_i \mathbb{I}_{\{y_j\}}(T(x_i)) \\
= & \sum_{\{i \in 1..m \mid T(x_i) = y_j\}} a_i
\end{aligned}
$$

---
乘积测度 $\mathbb{P}_X \otimes \mathbb{P}_Y$ 仅代表独立的联合分布（在离散代数下对应秩一矩阵 $r c^\mathrm{T}$），它仅是集合 $U(r,c)$ 内部的一个特异单点元素。

多面体 $U(r,c)$ 本质上是满足边际推前约束的全部耦合测度族 $\Pi(\mathbb{P}_X, \mathbb{P}_Y)$：
$$
\Pi(\mathbb{P}_X, \mathbb{P}_Y) = \{ \mathbb{P}_{(X,Y)} \in \mathcal{M}(\mathcal{X} \times \mathcal{Y}) \mid (\pi_1)_* \mathbb{P}_{(X,Y)} = \mathbb{P}_X, \, (\pi_2)_* \mathbb{P}_{(X,Y)} = \mathbb{P}_Y \}
$$
集合中的任意联合测度元素并非简单的乘积，而是依赖转移核生成的半直积测度 $\mathbb{P}_{(X,Y)} = \mathbb{P}_X \ltimes \mathbb{P}_{Y \mid X}$。

---
离散矩阵内积 $\langle P, C \rangle = \sum_{i,j} P_{ij} C_{ij}$ 本质上是代价函数 $c(x,y)$ 关于经验联合测度 $\mathbb{P}_{(X,Y)} = \sum_{i,j} P_{ij} \delta_{(x_i, y_j)}$ 的勒贝格积分期望：
$$
\langle P, C \rangle = \int_{\mathcal{X} \times \mathcal{Y}} c(x, y) \, \mathrm{d}\mathbb{P}_{(X,Y)}(x, y) = \mathbb{E}_{(X,Y) \sim \mathbb{P}_{(X,Y)}}[c(X,Y)]
$$
在连续概率空间中，该离散和瞬时泛化为连续代价核与联合概率密度的重积分对偶配对 $\langle c, \mathbb{P}_{(X,Y)} \rangle = \iint_{\mathcal{X} \times \mathcal{Y}} c(x, y) p(x, y) \, \mathrm{d}v(x) \mathrm{d}v(y)$。

---
在测度与信息论视域下，目标泛函等价于在耦合流形上最小化传输能量与互信息的加权和：
$$
\mathbb{P}_{(X,Y)}^\varepsilon = \operatorname*{argmin}_{\mathbb{P}_{(X,Y)} \in \Pi(\mathbb{P}_X, \mathbb{P}_Y)} \left( \mathbb{E}[c(X,Y)] + \varepsilon D_{\mathrm{KL}}(\mathbb{P}_{(X,Y)} \| \mathbb{P}_X \otimes \mathbb{P}_Y) \right)
$$
在离散矩阵空间 $U(r,c)$ 下引入边际推前约束的对偶乘子 $\alpha, \beta \in \mathbb{R}^d$，构造拉格朗日函数：
$$
\mathcal{L}(P, \alpha, \beta) = \langle P, M \rangle + \varepsilon \sum_{i,j} p_{ij} \log p_{ij} + \alpha^\mathrm{T}(P\mathbf{1}_d - r) + \beta^\mathrm{T}(P^\mathrm{T}\mathbf{1}_d - c)
$$
负熵的严格凸性确保全局极值唯一，令一阶变分导数归零 $\frac{\partial \mathcal{L}}{\partial p_{ij}} = m_{ij} + \varepsilon(1 + \log p_{ij}) + \alpha_i + \beta_j = 0$，解得 Gibbs 测度形式：
$$
p_{ij} = \exp\left(-\frac{\alpha_i + \varepsilon/2}{\varepsilon}\right) \exp\left(-\frac{m_{ij}}{\varepsilon}\right) \exp\left(-\frac{\beta_j + \varepsilon/2}{\varepsilon}\right)
$$
定义 Gibbs 积分核 $K := \exp(-M/\varepsilon)$ 与对偶缩放向量 $u := e^{-(\alpha + \varepsilon/2)/\varepsilon}, \, v := e^{-(\beta + \varepsilon/2)/\varepsilon}$，最优耦合瞬时塌缩为矩阵对角缩放：
$$
P^\varepsilon = \operatorname{diag}(u) K \operatorname{diag}(v), \quad \text{其中 } u \odot (K v) = r, \; v \odot (K^\mathrm{T} u) = c
$$

# 附录
## 各类杂项收集
对任意概率测度与任意随机变量（离散、连续乃至奇异），由测度前推与函数拉回的对偶性，恒有：
$$
\langle \mathbb{I}_A \otimes \mathbf{1}_{\mathcal{Y}}, \mathbb{P}_{(X,Y)} \rangle = \langle \pi_1^* \mathbb{I}_A, \mathbb{P}_{(X,Y)} \rangle = \langle \mathbb{I}_A, (\pi_1)_* \mathbb{P}_{(X,Y)} \rangle = \langle \mathbb{I}_A, \mathbb{P}_X \rangle
$$