# section 1
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
用此公式可以推导出，对于两个均匀离散分布而言，$T$ 的存在性等价于整除关系 $n \mid m$。具体而言，这是说：
- 设置矩阵 $P_{i,j} := \mathbb{P}_{Y \mid X=x_i}(\{y_j\}) = \mathbb{I}_{\{y_j\}}(T(x_i)) = \delta_{T(x_i)}(\{y_j\}) \in \{0, 1\}$，质量守恒给出 $\sum_{i = 1}^m P_{i,j} a_i = b_j \Leftarrow \sum_{i \in 1..m \mid T(x_i) = y_j} a_i = b_j$；
- 另一方面，$\sum_{j = 1}^n P_{i,j} = 1$，即每个源点 $x_i$ 只能被映射到一个目标点 $y_j$，此严格证明可以考虑
$$
\begin{aligned}
& \mathbb{P}_Y(\{T(x_i)\}) = (T_* \mathbb{P}_X)(\{T(x_i)\}) = \mathbb{P}_X(T^{-1}(\{T(x_i)\})) \geqslant \mathbb{P}_X(\{x_i\}) = a_i > 0 \\
& \Rightarrow T(x_i) \in \operatorname{supp}(\mathbb{P}_Y) \Rightarrow \\
& \sum_{j=1}^n \Pi_{i,j} = \sum_{j=1}^n \delta_{T(x_i)}(\{y_j\}) = \delta_{T(x_i)}\!\left(\bigcup_{j=1}^n \{y_j\}\right) = \delta_{T(x_i)}(\operatorname{supp}(\mathbb{P}_Y)) = 1
\end{aligned}
$$

另外还可以考虑 
$$
\begin{aligned}
& b_j = \langle \langle \mathbb{I}_{\{y_{j}\}}, \delta_{y_{1..n}} \rangle, b_{1..n}\rangle = \langle\mathbb{I}_{\{y_{j}\}}, \langle \delta_{y_{1..n}}, b_{1..n} \rangle\rangle = \langle\mathbb{I}_{\{y_{j}\}},\mathbb{P}_{Y} \rangle \\
= & \langle\mathbb{I}_{\{y_{j}\}},T_*\mathbb{P}_{X} \rangle = \langle T^* \mathbb{I}_{\{y_{j}\}},\mathbb{P}_{X} \rangle = \langle T^* \mathbb{I}_{\{y_{j}\}}, \langle \delta_{x_{1..m}} , a_{1..m}\rangle\rangle \\
= & \langle \langle \mathbb{I}_{\{y_{j}\}}, \delta_{T\circ x_{1..m}}\rangle,a_{1..m}\rangle = \langle P_{1..m,j},a_{1..m}\rangle
\end{aligned}
$$

按照方程 $\langle b_{1..n}| =  \langle \Pi_{1..m,1..n}|a_{1..m}\rangle$，带入 $a_{1..m} = \bm{1}_m/m,b_{1..n} = \bm{1}_n/n$，就容易看出 $n \mid m$ 是方程有解 $\Pi$ 的充要条件。其中充分性考虑构造 $\Pi = \bm{I}_n \otimes_k \bm{1}_{m/n} \in \{0,1\}^{m \times n}$。此时直接计算验证有 
$$
\begin{aligned}
& P \bm{1}_{n} = (\bm{I}_n \otimes_k \mathbf{1}_{m/n})(\mathbf{1}_n \otimes_k 1) = (\bm{I}_n \mathbf{1}_n) \otimes_k (\mathbf{1}_{m/n} \cdot 1) = \mathbf{1}_m \\
& P^{\mathrm{T}}\bm{1}_m/m = (\bm{I}_n \otimes_k \mathbf{1}_{m/n}^{\mathrm{T}})(\mathbf{1}_n \otimes_k \mathbf{1}_{m/n})/m = (\bm{I}_n \mathbf{1}_n) \otimes_k (\mathbf{1}_{m/n}^{\mathrm{T}} \cdot \mathbf{1}_{m/n})/m = \bm{1}_{n}/n
\end{aligned}
$$

---
设
$$
\mathbb{P}_{(X,Y)} = \sum_{i,j} \Pi_{ij} \, \delta_{x_i} \otimes_t \delta_{y_j}.
$$

为了以一种和谐的方式来导出边缘条件，首先我希望研究说明投影式 $(\pi_{1..N})_*\mathbb{P}_{X_{1..N}} = (\mathbb{P}_{X_i})_{i = 1..N}$

---
# section 2
乘积测度 $\mathbb{P}_X \otimes \mathbb{P}_Y$ 仅代表独立的联合分布（在离散代数下对应秩一矩阵 $r c^\mathrm{T}$），它仅是集合 $U(r,c)$ 内部的一个特异单点元素。

多面体 $U(r,c)$ 本质上是满足边际推前约束的全部耦合测度族 $\Pi(\mathbb{P}_X, \mathbb{P}_Y)$：
$$
\Pi(\mathbb{P}_X, \mathbb{P}_Y) = \{ \mathbb{P}_{(X,Y)} \in \mathcal{M}_{+}^{1}(\mathcal{X} \times \mathcal{Y}) \mid (\pi_1)_* \mathbb{P}_{(X,Y)} = \mathbb{P}_X, \, (\pi_2)_* \mathbb{P}_{(X,Y)} = \mathbb{P}_Y \}
$$
集合中的任意联合测度元素并非简单的乘积，而是依赖转移核生成的半直积测度 $\mathbb{P}_{(X,Y)} = \mathbb{P}_X \ltimes \mathbb{P}_{Y \mid X}$。

---
目标函数为
$$
\mathbb{P}_{(X,Y)}^\varepsilon = \operatorname*{argmin}_{\mathbb{P}_{(X,Y)} \in \Pi(\mathbb{P}_X, \mathbb{P}_Y)} \left( \mathbb{E}_{(X,Y) \sim \mathbb{P}_{(X,Y)}}[c(X,Y)] + \varepsilon D_{\mathrm{KL}}(\mathbb{P}_{(X,Y)} \| \mathbb{P}_X \otimes \mathbb{P}_Y) \right)
$$
在离散矩阵空间 $U(r,c)$ 下引入边际推前约束的对偶乘子 $\alpha, \beta \in \mathbb{R}^d$，构造拉格朗日函数：
$$
\mathcal{L}(P, \alpha, \beta) = \langle P, M \rangle + \varepsilon \sum_{i,j} p_{ij} \log p_{ij} + \alpha^\mathrm{T}(P\mathbf{1}_d - r) + \beta^\mathrm{T}(P^\mathrm{T}\mathbf{1}_d - c)
$$

# 附录
## 各类杂项收集
对任意概率测度与任意随机变量（离散、连续乃至奇异），由测度前推与函数拉回的对偶性，恒有：
$$
\langle \mathbb{I}_A \otimes \mathbf{1}_{\mathcal{Y}}, \mathbb{P}_{(X,Y)} \rangle = \langle \pi_1^* \mathbb{I}_A, \mathbb{P}_{(X,Y)} \rangle = \langle \mathbb{I}_A, (\pi_1)_* \mathbb{P}_{(X,Y)} \rangle = \langle \mathbb{I}_A, \mathbb{P}_X \rangle
$$