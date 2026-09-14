### 从经验测度到离散期望积分

设状态样本集合为 $x_{1..N} = (x_1, \dots, x_N)$，其中每个粒子 $x_j \in V = \mathbb{R}^n$。粒子群表示矩阵 $\bm{X} = (x_1, \dots, x_N) \in M_{n,N}(\mathbb{R})$。

在状态空间 $V$ 上，经验测度 $\mathbb{P}_N$ 由各样本点的 Dirac 测度等权叠加给出：
$$
\hat{\mathbb{P}}_{N;x_{1..N}} = \frac{1}{N} \sum_{j=1}^N \delta_{x_j}
$$

对任意可测映射 $f: \mathbb{R}^n \to \mathbb{R}^m$，其关于经验测度的期望积分退化为样本点上的离散求和：
$$
\mathbb{E}_{X \sim \hat{\mathbb{P}}_{N;x_{1..N}} }[f(X)] = \int_{\mathbb{R}^n} f \, \mathrm{d}\hat{\mathbb{P}}_{N;x_{1..N}}  = \frac{1}{N} \sum_{j=1}^N f(x_j)
$$

---

设样本索引空间为 $W = \mathbb{R}^{1 \times N}$，常数基准向量记为 $\mathbf{1}_N = (1, \dots, 1)^\mathrm{T}$。
由 $\mathbf{1}_N$ 张成的一维均值子空间诱导正交投影矩阵与对应的去均值余投影矩阵（中心化算子）：
$$
\bm{P}_{\mathbf{1}_N} = \frac{1}{N} \mathbf{1}_N \mathbf{1}_N^\mathrm{T}, \qquad \bm{P}_{\mathbf{1}_N}^\perp = \bm{I}_N - \frac{1}{N} \mathbf{1}_N \mathbf{1}_N^\mathrm{T}
$$
余投影矩阵 $\bm{P}_{\mathbf{1}_N}^\perp$ 具备对称幂等性 $(\bm{P}_{\mathbf{1}_N}^\perp)^2 = \bm{P}_{\mathbf{1}_N}^\perp = (\bm{P}_{\mathbf{1}_N}^\perp)^\mathrm{T}$，其秩与迹严格满足 $\mathrm{tr}(\bm{P}_{\mathbf{1}_N}^\perp) = \operatorname{rank}(\bm{P}_{\mathbf{1}_N}^\perp) = N - 1$。
对常数均值子空间，该算子具有严格的零化湮灭性质：
$$
\bm{P}_{\mathbf{1}_N}^\perp \mathbf{1}_N = \mathbf{0}, \qquad \mathbf{1}_N^\mathrm{T} \bm{P}_{\mathbf{1}_N}^\perp = \mathbf{0}^\mathrm{T}
$$
将集合矩阵 $\bm{X} = (x_1, \dots, x_N) \in M_{n,N}(\mathbb{R})$ 在样本索引维度执行右侧正交直和分解：
$$
\bm{X} = \bm{X} \bm{P}_{\mathbf{1}_N} + \bm{X} \bm{P}_{\mathbf{1}_N}^\perp
$$
均值投影项退化为经验均值场的秩一矩阵 $\bm{X} \bm{P}_{\mathbf{1}_N} = \bar{x} \mathbf{1}_N^\mathrm{T} = (\bar{x}, \dots, \bar{x})$，其中经验均值为 $\bar{x} = \frac{1}{N}\bm{X}\mathbf{1}_N$。
余投影项导出严格属于零均值正交补子空间 $(\mathbf{1}_N)^\perp$ 的集合扰动矩阵（ensemble anomalies）：
$$
\bm{A}_X := \bm{X} \bm{P}_{\mathbf{1}_N}^\perp = (x_1 - \bar{x}, \dots, x_N - \bar{x}) \in M_{n,N}(\mathbb{R})
$$

---

设连续空间真投影内积为 $\langle \mathscr{P}_1^\perp U, \mathscr{P}_1^\perp V \rangle_{\mathcal{H}}$，经验测度 $\mathbb{P}_N$ 诱导的唯一离散内积为 $\langle \bm{U}, \bm{V} \rangle_{\mathbb{P}_N} = \frac{1}{N}\bm{U}\bm{V}^\mathrm{T}$。
将去中心化集合 $\bm{U}\bm{P}_{\mathbf{1}_N}^\perp$ 与 $\bm{V}\bm{P}_{\mathbf{1}_N}^\perp$ 作用于经验内积，由余投影对称幂等性得：
$$
\langle \bm{U}\bm{P}_{\mathbf{1}_N}^\perp, \bm{V}\bm{P}_{\mathbf{1}_N}^\perp \rangle_{\mathbb{P}_N} = \frac{1}{N} (\bm{U}\bm{P}_{\mathbf{1}_N}^\perp)(\bm{V}\bm{P}_{\mathbf{1}_N}^\perp)^\mathrm{T} = \frac{1}{N}\bm{U}\bm{P}_{\mathbf{1}_N}^\perp\bm{V}^\mathrm{T}
$$
在乘积测度 $\mathbb{P}^{\otimes N}$ 下取期望，常数均值项被余投影湮灭，余项由迹精确收缩：
$$
\mathbb{E}_{\mathbb{P}^{\otimes N}}\left[ \langle \bm{U}\bm{P}_{\mathbf{1}_N}^\perp, \bm{V}\bm{P}_{\mathbf{1}_N}^\perp \rangle_{\mathbb{P}_N} \right] = \frac{\mathrm{tr}(\bm{P}_{\mathbf{1}_N}^\perp)}{N} \langle \mathscr{P}_1^\perp U, \mathscr{P}_1^\perp V \rangle_{\mathcal{H}} = \frac{N - 1}{N} \langle \mathscr{P}_1^\perp U, \mathscr{P}_1^\perp V \rangle_{\mathcal{H}}
$$
反解真实真投影内积，直接消除几何降维带来的压缩因子：
$$
\langle \mathscr{P}_1^\perp U, \mathscr{P}_1^\perp V \rangle_{\mathcal{H}} = \mathbb{E}_{\mathbb{P}^{\otimes N}}\left[ \frac{N}{N - 1} \langle \bm{U}\bm{P}_{\mathbf{1}_N}^\perp, \bm{V}\bm{P}_{\mathbf{1}_N}^\perp \rangle_{\mathbb{P}_N} \right]
$$
由此，采样集合矩阵对真投影内积的无偏估计子自然定义为：
$$
\widehat{\Sigma}_{UV} := \frac{N}{N - 1} \langle \bm{U}\bm{P}_{\mathbf{1}_N}^\perp, \bm{V}\bm{P}_{\mathbf{1}_N}^\perp \rangle_{\mathbb{P}_N} = \frac{1}{N - 1} \bm{U}\bm{P}_{\mathbf{1}_N}^\perp\bm{V}^\mathrm{T}
$$

---
当然，也可以考虑用 $\mathscr{P}_1,\mathscr{P}_1^\perp$ 拆分 $U,V$，并计算有
$$
\Sigma_{UV}:=\langle\mathscr P_1^\perp U,\mathscr P_1^\perp V\rangle_{\mathcal H}
=\langle U,V\rangle_{\mathcal H}-\langle\mathscr P_1U,\mathscr P_1V\rangle_{\mathcal H}.
$$
而 $\langle U, V \rangle_{\mathcal{H}} = \int_\Omega U V^\mathrm{T} \, \mathrm{d}\mathbb{P}$，利用 $\mathbb{E}_{\mathbb{P}^{\otimes N}}[\mathbb{P}_N] = \mathbb{P}$，计算有
$$
\int_\Omega U V^\mathrm{T} \, \mathrm{d}\mathbb{P} = \int_\Omega U V^\mathrm{T} \, \mathrm{d}\left( \mathbb{E}_{\mathbb{P}^{\otimes N}}[\mathbb{P}_N] \right) = \mathbb{E}_{\mathbb{P}^{\otimes N}}\left[ \int_\Omega U V^\mathrm{T} \, \mathrm{d}\mathbb{P}_N \right] = \mathbb{E}_{\mathbb{P}^{\otimes N}}\left[ \langle \bm{U}, \bm{V} \rangle_{\mathbb{P}_N} \right]
$$


---
# 附录
## 随机源, $\mathbb{P}_N,\mathbb{P}^{\otimes N}$
对于给定的随机采样实现（即由随机源或特定种子 seed 确定的样本轨道 $\omega \in \Omega$），粒子点集 $\{x_j(\omega)\}_{j=1}^N$ 诱导了一个从状态底空间 $\mathcal{X}$（例如 $\mathbb{R}^n$）出发的线性点态采样算子：
$$
\mathscr{S}_N^{(\omega)}: L^2(\mathcal{X}, \mathbb{P}) \to (\mathbb{R}^n)^N, \quad U \mapsto (U(x_1(\omega)), \dots, U(x_N(\omega)))
$$
当我们在离散样本空间赋予标准的缩放欧氏内积 $\langle \bm{u}, \bm{v} \rangle_{\ell_N^2} = \frac{1}{N} \bm{u} \bm{v}^\mathrm{T}$ 时，经验内积正是此采样算子作用下的度规拉回：
$$
\langle U, V \rangle_{\mathbb{P}_N} = \langle \mathscr{S}_N^{(\omega)} U, \mathscr{S}_N^{(\omega)} V \rangle_{\ell_N^2} = \frac{1}{N} \sum_{j=1}^N U(x_j(\omega)) V(x_j(\omega))^\mathrm{T}
$$
种子 seed 在此扮演了从无限维连续轨道空间截取具体采样切片的参数化角色。

---
定理: $\mathbb{E}_{\mathbb{P}^{\otimes N}}[\mathbb{P}_N] = \mathbb{P}$
证明: 

---
将外积映射视为状态空间上的连续双线性张量核 $K(U, V)(\omega) := U(\omega) V(\omega)^\mathrm{T}$。
经验内积严格表现为核函数 $K(U, V)$ 与随机经验测度 $\mathbb{P}_N = \frac{1}{N}\sum_{j=1}^N \delta_{\omega_j}$ 的泛函对偶配对：
$$
\frac{1}{N} \bm{U}\bm{V}^\mathrm{T} = \int_\Omega K(U, V) \, \mathrm{d}\mathbb{P}_N = \langle K(U, V), \mathbb{P}_N \rangle
$$
在测度对偶空间中，经验测度关于样本全测度的 Bochner 期望恒等于真测度 $\mathbb{E}_{\mathbb{P}^{\otimes N}}[\mathbb{P}_N] = \mathbb{P}$。
利用对偶配对与期望算子的线性交换律，无需任何坐标求和即可瞬时完成证明：
$$
\mathbb{E}_{\mathbb{P}^{\otimes N}}\left[ \frac{1}{N} \bm{U}\bm{V}^\mathrm{T} \right] = \langle K(U, V), \mathbb{E}_{\mathbb{P}^{\otimes N}}[\mathbb{P}_N] \rangle = \langle K(U, V), \mathbb{P} \rangle = \langle U, V \rangle_{\mathcal{H}}
$$

## 经验测度与积分核
将离散经验内积视作广义积分核作用于测试函数对偶：$\frac{1}{N}\bm{U}\bm{V}^\mathrm{T} = \iint u(x) v(y)^\mathrm{T} K_N(x, y) \, \mathrm{d}x \mathrm{d}y$。
经验核由样本沿对角线张成 $K_N(x, y) := \frac{1}{N} \sum_{j=1}^N \delta(x - x_j) \delta(y - x_j) \in \mathcal{D}'(\mathbb{R}^n \times \mathbb{R}^n)$。
在广义函数弱拓扑下取期望，单点筛选性质导出对角密度奇异核：
$$
\mathbb{E}_{\mathbb{P}^{\otimes N}}[K_N(x, y)] = \int \delta(x - z) \delta(y - z) p(z) \, \mathrm{d}z = \delta(x - y) p(x)
$$
将期望极限核代入双线性形式，对角 Dirac 测度 $\delta(x - y)$ 促使二重积分瞬间塌缩：
$$
\iint u(x) v(y)^\mathrm{T} \delta(x - y) p(x) \, \mathrm{d}x \mathrm{d}y = \int u(x) v(x)^\mathrm{T} p(x) \, \mathrm{d}x = \langle U, V \rangle_{\mathcal{H}}
$$
该物理图像揭示了经验内积在分布意义下，正是对连续对角测度流 $\delta(x - y) \mathrm{d}\mathbb{P}_X(x)$ 的有限粒子离散逼近。以及
$$
K_N(x, y) = \frac{1}{N} \sum_{j=1}^N \delta(x - x_j) \delta(y - x_j)\rightharpoonup \delta(x - y) p(x)
$$

## $\mathbb{P}$ 投影的一些计算
坐标投影的边缘测度满足 $(\pi_i)_\#\mathbb P^{\otimes N}=\mathbb P$. 

在有界可测函数空间 $B_b(\Omega)$ 与测度空间 $\mathcal{M}(\Omega)$ 的对偶配对下，测度完全由对偶配对 $\langle f, \mu \rangle = \int_\Omega f \, \mathrm{d}\mu$ 唯一刻画。
对任意测试函数 $f \in B_b(\Omega)$，作用于随机经验测度 $\mathbb{P}_N = \frac{1}{N}\sum_{j=1}^N \delta_{\omega_j}$：
$$
\langle f, \mathbb{P}_N \rangle = \frac{1}{N}\sum_{j=1}^N f(\omega_j)
$$
对该标量随机变量取全测度期望，由各边际独立同分布测度直接结算：
$$
\mathbb{E}_{\mathbb{P}^{\otimes N}}\left[ \langle f, \mathbb{P}_N \rangle \right] = \frac{1}{N}\sum_{j=1}^N \mathbb{E}_{\mathbb{P}}[f] = \int_\Omega f \, \mathrm{d}\mathbb{P} = \langle f, \mathbb{P} \rangle
$$
或者
$$
\mathbb{E}_{\mathbb{P}^{\otimes N}}[\langle f, \mathbb{P}_N \rangle] = \int_{\Omega^N} \left( \frac{1}{N} \sum_{j=1}^N f(\omega_j) \right) \mathrm{d}\mathbb{P}^{\otimes N}(\bm{\omega}) = \frac{1}{N} \sum_{j=1}^N \int_{\Omega^N} f(\omega_j) \, \mathrm{d}\mathbb{P}^{\otimes N}(\bm{\omega})
$$
对固定指标 $j$，被积项仅依赖第 $j$ 坐标，由 Fubini 定理分解测度并结合全概率归一化 $\mathbb{P}(\Omega) = 1$：
$$
\int_{\Omega^N} f(\omega_j) \, \mathrm{d}\mathbb{P}^{\otimes N}(\bm{\omega}) = \int_\Omega f(\omega_j) \, \mathrm{d}\mathbb{P}(\omega_j) \cdot \prod_{k \neq j} \int_\Omega 1 \, \mathrm{d}\mathbb{P}(\omega_k) = \int_\Omega f \, \mathrm{d}\mathbb{P} = \langle f, \mathbb{P} \rangle
$$
于是有 $\langle f, \mathbb{E}_{\mathbb{P}^{\otimes N}}[\mathbb{P}_N] \rangle = \mathbb{E}_{\mathbb{P}^{\otimes N}}[\langle f, \mathbb{P}_N \rangle] = \langle f, \mathbb{P} \rangle$，进而 $\mathbb{E}_{\mathbb{P}^{\otimes N}}[\mathbb{P}_N] = \mathbb{P}$。