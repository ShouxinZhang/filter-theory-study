定理（联合高斯下条件期望的线性性 / MMSE 等价于 LMMSE）：
设随机变量 $X, Y \in \mathcal{H} = L^2(\Omega, \mathcal{F}, \mathbb{P})$ 服从联合高斯分布，定义空间 $\mathcal{G}_Y := L^2(\sigma(Y))$ 与 $\mathcal{L}_Y := \mathrm{span}\{1, Y\}$。
则条件期望算子（全可测空间投影）与仿射线性投影完全重合：
$$
\mathbb{E}[X \mid Y] = \mathscr{P}_{\mathcal{G}_Y} X = \mathscr{P}_{\mathcal{L}_Y} X
$$
证明: 1. 空间混沌分解：由单变量高斯空间 Wiener 混沌分解，全可测空间正交直和分解为 $\mathcal{G}_Y = \bigoplus_{n=0}^\infty \mathcal{H}_n(Y)$，其中第 $n$ 混沌为 $\mathcal{H}_n(Y) = \mathrm{span}\{ H_n( \frac{\mathscr{P}_1^\perp Y}{\|\mathscr{P}_1^\perp Y\|_{\mathcal{H}}} ) \}$。
2. 线性子空间对应：线性估计空间严格对应前两阶混沌的直和，即 $\mathcal{L}_Y = \mathcal{H}_0(Y) \oplus \mathcal{H}_1(Y) = \mathrm{span}\{1\} \oplus \mathrm{span}\{\mathscr{P}_1^\perp Y\}$。
3. 被估计量阶数定位：在联合高斯空间中分解 $X = \mathscr{P}_1 X + \mathscr{P}_1^\perp X$，其中 $\mathscr{P}_1 X$ 属于第零混沌，去中心化偏差 $\mathscr{P}_1^\perp X$ 纯属第一混沌。
4. 混沌阶数正交性：由联合高斯混沌的正交性 $\mathcal{H}_1 \perp \mathcal{H}_n \, (\forall n \ge 2)$，高阶内积恒为零，故 $\mathscr{P}_{\mathcal{H}_n(Y)} X = 0 \, (\forall n \ge 2)$。
5. 投影等价定解：总投影算子在高阶混沌上分量全消，截断至线性阶：
$$
\mathbb{E}[X \mid Y] = \mathscr{P}_{\mathcal{G}_Y} X = \sum_{n=0}^\infty \mathscr{P}_{\mathcal{H}_n(Y)} X = \mathscr{P}_{\mathcal{H}_0(Y)} X + \mathscr{P}_{\mathcal{H}_1(Y)} X = \mathscr{P}_{\mathcal{L}_Y} X
$$

---
去中心化偏差本身是关于常数空间的余投影（co-projection）：
$$
\mathscr{P}_1 X = \mathbb{E}[X], \qquad \mathscr{P}_1^\perp X = X - \mathscr{P}_1 X
$$
考虑$\mathcal{L}_Y = \mathrm{span}\{1, Y\}$，
对基底 $\{1, Y\}$ 执行 Gram-Schmidt 正交化，第二项替换为其关于第一项的正交余项 $\mathscr{P}_1^\perp Y = Y - \mathscr{P}_1 Y$。则
$$
\mathcal{L}_Y = \mathrm{span}\{1, Y\} = \mathrm{span}\{1\} \oplus \mathrm{span}\{\mathscr{P}_1^\perp Y\}
$$
对任意单维空间，一维投影恒有 $\mathscr{P}_v X = \frac{\langle X, v \rangle_{\mathcal{H}}}{\|v\|_{\mathcal{H}}^2} v$，在此取 $v = \mathscr{P}_1^\perp Y$，立得：
$$
\mathscr{P}_{\mathcal{L}_Y} X = (\mathscr{P}_1 + \mathscr{P}_{\mathscr{P}_1^\perp Y})X = \mathscr{P}_1 X + \frac{\langle \mathscr{P}_1^\perp X, \mathscr{P}_1^\perp Y \rangle_{\mathcal{H}}}{\langle \mathscr{P}_1^\perp Y, \mathscr{P}_1^\perp Y \rangle_{\mathcal{H}}} \mathscr{P}_1^\perp Y
$$

---