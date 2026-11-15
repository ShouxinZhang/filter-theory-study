# 离散 Monge 映射的存在条件 {#cw:app:monge}

**原子质量守恒：**设 $x_1,\dots,x_m$ 各自互异，$y_1,\dots,y_n$ 各自互异，$a_i,b_j>0$。若 $T_*\mathbb P_X=\mathbb P_Y$，则
$$ {#cw:eq:monge-atom-mass}
\begin{aligned}
b_j&=\mathbb E_{Y\sim\mathbb P_Y}[\mathbb I_{\{y_j\}}(Y)]
=\mathbb E_{X\sim\mathbb P_X}[\mathbb I_{\{y_j\}}(T(X))]\\
&=\int_{\mathcal S_X}\mathbb I_{\{y_j\}}(T(x))\,
\mathrm d\!\left(\sum_{i=1}^m a_i\delta_{x_i}\right)(x)
=\sum_{\{i:\,T(x_i)=y_j\}}a_i.
\end{aligned}
$$
每个正质量源点必然映入目标支撑，因为
$$ {#cw:eq:monge-support}
\mathbb P_Y(\{T(x_i)\})
=\mathbb P_X(T^{-1}(\{T(x_i)\}))\ge a_i>0.
$$
因此其条件概率矩阵为逐行单点选择，联合概率矩阵则带有源权重：
$$ {#cw:eq:monge-conditional}
\begin{aligned}
&P_{Y\mid X;i,j}=\mathbb I_{\{y_j\}}(T(x_i))\in\{0,1\},\qquad
\sum_{j=1}^n P_{Y\mid X;i,j}
=\delta_{T(x_i)}\!\left(\bigcup_{j=1}^n\{y_j\}\right)=1,\\
&\bm P_{Y\mid X}\mathbf1_n=\mathbf1_m,\qquad
\bm P_{Y\mid X}^{\mathrm T}\bm a=\bm b,\qquad
\bm\Pi=\operatorname{diag}(\bm a)\bm P_{Y\mid X}.
\end{aligned}
$$
同一质量关系也可以完全用推前与拉回对偶表达：
$$ {#cw:eq:monge-duality}
\begin{aligned}
b_j&=\langle\mathbb I_{\{y_j\}},\mathbb P_Y\rangle_{\mathcal S_Y}
=\langle\mathbb I_{\{y_j\}},T_*\mathbb P_X\rangle_{\mathcal S_Y}
=\langle T^*\mathbb I_{\{y_j\}},\mathbb P_X\rangle_{\mathcal S_X}\\
&=\left\langle T^*\mathbb I_{\{y_j\}},
\delta_{x_{1..m}}\bm a\right\rangle_{\mathcal S_X}
=\sum_{i=1}^m a_iP_{Y\mid X;i,j}.
\end{aligned}
$$

::: 定理 {#cw:thm:monge-divisibility} 均匀离散分布的整除条件

设源、目标分布分别均匀分布于 $m$ 个与 $n$ 个互异支撑点。存在可测映射 $T$ 满足 $T_*\mathbb P_X=\mathbb P_Y$，当且仅当 $n\mid m$。

:::

::: 证明

必要性：由{@cw:eq:monge-atom-mass}，每个目标点的原像必须含有 $m/n$ 个源点：
$$ {#cw:eq:monge-divisibility}
\frac1n=\frac1m\#\{i:T(x_i)=y_j\}
\quad\Longrightarrow\quad\frac mn\in\mathbb N.
$$
充分性：若 $m=nq$，将每 $q$ 个源点分配给一个目标点。用矩阵分块直积写为
$$ {#cw:eq:monge-construction}
\begin{aligned}
&\bm P_{Y\mid X}=\bm I_n\otimes_k\mathbf1_q\in\{0,1\}^{m\times n},
\qquad\bm\Pi=\frac1m\bm P_{Y\mid X},\\
&\bm P_{Y\mid X}\mathbf1_n
=(\bm I_n\otimes_k\mathbf1_q)(\mathbf1_n\otimes_k1)
=\mathbf1_n\otimes_k\mathbf1_q=\mathbf1_m,\\
&\bm P_{Y\mid X}^{\mathrm T}\frac{\mathbf1_m}{m}
=\frac{(\bm I_n\otimes_k\mathbf1_q^{\mathrm T})(\mathbf1_n\otimes_k\mathbf1_q)}m
=\frac q m\mathbf1_n=\frac1n\mathbf1_n.
\end{aligned}
$$
以矩阵每行的唯一非零元素确定 $T(x_i)$，并在有限源支撑之外任取常值延拓，即得到所需可测映射。

:::
