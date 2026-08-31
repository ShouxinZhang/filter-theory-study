# 线性滤波 Gram-Schmidt 几何推导

> 基于 Hilbert 模（打到模的 H-空间）正交投影的 Kalman 滤波推导 — 符号体系与 Step 0–5 全流程

---

## 一、符号习惯体系

在整个 Gram-Schmidt 几何推导中建立的无歧义、高度严谨的 Hilbert 模符号习惯如下（内积打到矩阵代数，见 §1 注记）。

### 1. 空间与内积结构（Hilbert 模）

- **全空间**：$\mathcal{H} = L^2(\Omega, \mathcal{F}, P; \mathbb{R}^n)$，平方可积 $n$ 维随机向量空间。
- **模值内积**：$\langle A, B \rangle := \mathbb{E}[A B^\mathrm{T}] \in \mathbb{R}^{n \times n}$，取值于矩阵代数而非标量域，故严格来说 $\mathcal{H}$ 是 **Hilbert 模（Hilbert C*-模）**而非经典 Hilbert 空间——即“打到模的 H-空间”。
- **观测子模**：$\mathcal{Y}_k = \text{span}\{Y_1, \dots, Y_k\} \subset \mathcal{H}$，作为 $\mathcal{H}$ 的闭子模（有限维观测张成的子模，投影定理仍成立）。

> **定义 1.1（Hilbert C*-模，左模）** 设 $\mathcal{A}$ 为含单位元的 C*-代数，$*$ 为其对合。左 $\mathcal{A}$-模 $\mathcal{H}$ 若配备映射 $\langle\cdot,\cdot\rangle:\mathcal{H}\times\mathcal{H}\to\mathcal{A}$ 满足
> (i) $\langle x,x\rangle \in \mathcal{A}_+$ 且 $\langle x,x\rangle = 0_{\mathcal{A}} \iff x = 0$；
> (ii) $\langle x,y\rangle = \langle y,x\rangle^*$；
> (iii) $\langle a\cdot x, y\rangle = a\langle x,y\rangle$, $\forall a\in\mathcal{A},\;x,y\in\mathcal{H}$（蕴含 $\langle x,a\cdot y\rangle = \langle x,y\rangle a^*$）；
> (iv) $\mathcal{H}$ 关于范数 $\|x\|_{\mathcal{H}} := \|\langle x,x\rangle\|_{\mathcal{A}}^{1/2}$ 完备，
> 则称 $(\mathcal{H},\langle\cdot,\cdot\rangle)$ 为 Hilbert $\mathcal{A}$-模。此时 $\langle x,y\rangle\langle y,x\rangle \preceq \|\langle y,y\rangle\|_{\mathcal{A}}\,\langle x,x\rangle$（Cauchy–Schwarz），正交性定义为 $\langle x,y\rangle = 0_{\mathcal{A}}$。当 $\mathcal{A}=\mathbb{R}$（或 $\mathbb{C}$）时退化为经典 Hilbert 空间。

> **例 1.2（本文构造）** 取 $\mathcal{A}=M_n(\mathbb{R})$，$a^*:=a^{\mathrm{T}}$，$\mathcal{H}:=L^2(\Omega,\mathcal{F},P;\mathbb{R}^n)$，左作用 $(a\cdot X)(\omega):=aX(\omega)$，$\langle X,Y\rangle:=\mathbb{E}[XY^{\mathrm{T}}]\in\mathcal{A}$。则 (i)–(iii) 由期望之线性性及 $a\mathbb{E}[XY^{\mathrm{T}}]=\mathbb{E}[(aX)Y^{\mathrm{T}}]$ 得证，$\langle X,X\rangle\succeq 0$ 即协方差矩；$\|X\|_{\mathcal{H}}^2 = \mathrm{tr}\langle X,X\rangle = \mathbb{E}[\|X\|_2^2]$ 与 $\|\langle X,X\rangle\|_{\mathcal{A}}^{1/2}$ 等价，故完备性即 $L^2$ 完备性。此即 $\mathcal{A}=M_n(\mathbb{R})$ 上的 Hilbert 模——本文所谓“打到模的 H-空间”。有限生成闭子模 $\mathcal{Y}_k$ 之模正交补 $\mathcal{Y}_k^\perp:=\{x\in\mathcal{H}:\langle x,y\rangle=0_{\mathcal{A}},\forall y\in\mathcal{Y}_k\}$ 存在且 $\mathcal{H}=\mathcal{Y}_k\oplus\mathcal{Y}_k^\perp$，故正交投影 $\mathscr{P}_{\mathcal{Y}_k}$ 及其 co-proj $\mathscr{P}_{\mathcal{Y}_k}^\perp$ 良定。

### 2. 核心算子体系（模上投影）

- **正交投影算子**：$\mathscr{P}_{\mathcal{G}}$，向闭子模 $\mathcal{G}$ 的正交投影（模意义下 $\langle\cdot,\cdot\rangle=0_{n\times n}$）。
- **co-proj 算子（正交补投影算子）**：

$$
\mathscr{P}_{\mathcal{G}}^\perp := \mathscr{I}_{\mathcal{H}} - \mathscr{P}_{\mathcal{G}}
$$

用于替代传统的 tilde 符号与误差算子，统一表示正交补投影；$\mathcal{H} = \mathcal{G} \oplus \mathcal{G}^\perp$ 为模直和。

### 3. 状态估计与协方差

- **先验 / 后验估计**：$x_k^- = \mathscr{P}_{\mathcal{Y}_{k-1}} X_k$，$x_k^+ = \mathscr{P}_{\mathcal{Y}_k} X_k$。
- **先验 / 后验协方差**：

$$
P_k^- = \langle \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp X_k, \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp X_k \rangle, \quad P_k^+ = \langle \mathscr{P}_{\mathcal{Y}_k}^\perp X_k, \mathscr{P}_{\mathcal{Y}_k}^\perp X_k \rangle
$$

- **噪声方差**：$Q = \langle W_k, W_k \rangle$，$R = \langle V_k, V_k \rangle$。

### 4. 增量与增益项

- **观测 co-proj（新息）**：理论表达为 $\mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k = H \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp X_k + V_k$，样本数值为 $y_k - H x_k^-$。
- **卡尔曼增益**：

$$
K_k = \langle X_k, \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k \rangle \langle \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k, \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k \rangle^{-1}
$$

> 该体系将算子理论、泛函分析与滤波算法无缝结合，全程无非齐次项，完全在正交子模及其补模中完成。

---

## 二、Gram-Schmidt 正交化推导全流程（Step 0 – Step 5）

### Step 0 — 系统模型与 Hilbert 模底层框架

线性无控制系统：

$$
X_k = F X_{k-1} + W_{k-1}, \quad Y_k = H X_k + V_k
$$

Hilbert 模的矩阵值内积定义为（打到模，详见 §1 注记）：

$$
\langle A, B \rangle := \mathbb{E}[A B^\mathrm{T}] \in \mathbb{R}^{n\times n}, \quad \|A\|^2 := \mathrm{tr}\langle A,A\rangle
$$

子模投影记为 $\mathscr{P}_{\mathcal{G}}$，向其正交补投影的 **co-proj 算子** 定义为 $\mathscr{P}_{\mathcal{G}}^\perp := \mathscr{I} - \mathscr{P}_{\mathcal{G}}$（正交按 $\langle\cdot,\cdot\rangle = 0_{n\times n}$ 理解）。

### Step 1 — 先验预测与先验协方差

已知 $k-1$ 时刻后验投影 $x_{k-1}^+ = \mathscr{P}_{\mathcal{Y}_{k-1}} X_{k-1}$，则 $k$ 时刻先验估计即投影：

$$
x_k^- = \mathscr{P}_{\mathcal{Y}_{k-1}} X_k = F x_{k-1}^+
$$

将状态作用于 co-proj 算子，计算其自内积矩，得先验协方差矩阵：

$$
P_k^- = \langle \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp X_k, \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp X_k \rangle = F P_{k-1}^+ F^\mathrm{T} + Q
$$

### Step 2 — 新息构造与子空间直和分解

当新观测 $Y_k$ 到达时，将 $Y_k$ 作用于 co-proj 算子，提取与旧空间正交的新分量 $\mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k$。

由此，观测子模按 G-S 正交化直和分解为：

$$
\mathcal{Y}_k = \mathcal{Y}_{k-1} \oplus \text{span}\{\mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k\}
$$

### Step 3 — 后验估计与卡尔曼增益的通用内积形式

由正交投影的可加性，后验估计展开为：

$$
x_k^+ = \mathscr{P}_{\mathcal{Y}_k} X_k = x_k^- + \langle X_k, \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k \rangle \langle \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k, \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k \rangle^{-1} \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k
$$

卡尔曼增益定义为内积之商：

$$
K_k := \langle X_k, \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k \rangle \langle \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k, \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k \rangle^{-1}
$$

### Step 4 — 内积的显式展开

将观测方程作用 co-proj 算子得：

$$
\mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k = H \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp X_k + V_k
$$

利用正交性展开分子与分母：

$$
\langle X_k, \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k \rangle = \langle \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp X_k, \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp X_k \rangle H^\mathrm{T} = P_k^- H^\mathrm{T}
$$

$$
\langle \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k, \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k \rangle = H P_k^- H^\mathrm{T} + R
$$

代入即得经典形式：

$$
K_k = P_k^- H^\mathrm{T} (H P_k^- H^\mathrm{T} + R)^{-1}
$$

### Step 5 — 后验协方差

对状态 $X_k$ 作用新的 co-proj 算子 $\mathscr{P}_{\mathcal{Y}_k}^\perp$：

$$
\mathscr{P}_{\mathcal{Y}_k}^\perp X_k = \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp X_k - K_k \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp Y_k = (I - K_k H) \mathscr{P}_{\mathcal{Y}_{k-1}}^\perp X_k - K_k V_k
$$

计算其自内积矩，由噪声与状态正交性直接得出：

$$
P_k^+ = \langle \mathscr{P}_{\mathcal{Y}_k}^\perp X_k, \mathscr{P}_{\mathcal{Y}_k}^\perp X_k \rangle = (I - K_k H) P_k^-
$$

全程无非齐次项，完全在正交子空间及其补空间中优雅完成。
