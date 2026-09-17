长度或空间体积泛函直接由 $n$ 重微分形式的齐次缩并给出：

$$
\mathrm{d}s^n = \sum_{i_1, \dots, i_n} g_{i_1 \dots i_n} \, \mathrm{d}x^{i_1} \otimes \cdots \otimes \mathrm{d}x^{i_n}
$$

1. **$k$ 阶导数的高阶全对称张量本质**：$f: \mathbb{R}^d \to \mathbb{R}$ 的 $k$ 阶 Fréchet 导数是全对称 $k$ 阶协变张量 $D^k f(x) \in \operatorname{Sym}^k((\mathbb{R}^d)^*)$：

$$
(D^k f(x))_{i_1 \dots i_k} = \frac{\partial^k f(x)}{\partial x^{i_1} \cdots \partial x^{i_k}}
$$

2. **增量矢量的张量幂（Tensor Power）**：位移 $h \in \mathbb{R}^d$ 的 $k$ 重外张量积构成秩-1 全对称反变张量：

$$
h^{\otimes k} = \underbrace{h \otimes \cdots \otimes h}_{k \text{ 个}} \in \operatorname{Sym}^k(\mathbb{R}^d)
$$

3. **泰勒展开的张量全缩并**：多元渐近展开即高阶导数张量与位移张量幂的逐阶对偶缩并：

$$
f(x + h) = \sum_{k=0}^\infty \frac{1}{k!} \langle D^k f(x), h^{\otimes k} \rangle = \sum_{k=0}^\infty \frac{1}{k!} \sum_{i_1, \dots, i_k} \frac{\partial^k f(x)}{\partial x^{i_1} \cdots \partial x^{i_k}} h^{i_1} \cdots h^{i_k}
$$

4. **指数位移算子（Lie 算子表示）**：引入梯度算子张量 $\nabla \in (\mathbb{R}^d)^*$，展开式可严格写为算子指数形式：

$$
f(x + h) = \exp(\langle h, \nabla \rangle) f(x) = \sum_{k=0}^\infty \frac{1}{k!} (h \cdot \nabla)^k f(x)
$$

5. **组合数多项式定理的张量来源**：全张量缩并经过指标置换对称化后，多重指标组合数 $\binom{k}{\alpha} = \frac{k!}{\alpha_1! \cdots \alpha_d!}$ 恰为同一个多重偏导项在张量空间基底中的**置换轨道重数**：

$$
\frac{1}{k!} (h \cdot \nabla)^k = \frac{1}{k!} \sum_{|\alpha|=k} \binom{k}{\alpha} h^\alpha \partial^\alpha = \sum_{|\alpha|=k} \frac{h^\alpha}{\alpha!} \partial^\alpha
$$

6. **代数闭环**：高阶度规张量 $g^{(k)}$ 与高阶微商 $D^k f$ 均栖息于**对称代数 $\operatorname{Sym}(V^*)$** 中，$\exp(h \cdot \nabla)$ 是其在张量 Fock 空间上的泛函生成元。
