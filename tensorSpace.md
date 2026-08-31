# Old. 关于tensor的一些简单讨论

### **§1 基底系统与集合张量空间**

#### **定义 1.1（游标基底系统）**

通过指标标号区分物理空间与样本空间：

1. **物理状态基底**：$V = \mathbb{R}^n$ 的标准正交基记为列向量 $\{e_{V; i}\}_{i=1}^n$（$e_{V; i} \in \mathbb{R}^{n \times 1}$）。
2. **样本索引基底**：$W = \mathbb{R}^N$ 的标准正交基记为列向量 $\{e_{W; j}\}_{j=1}^N$（$e_{W; j} \in \mathbb{R}^{N \times 1}$）。
3. **样本对偶基底**：对偶空间 $W^* = (\mathbb{R}^N)^*$ 的对偶基记为行向量 $\{e_{W^*; j}\}_{j=1}^N$（$e_{W^*; j} \in \mathbb{R}^{1 \times N}$），满足对偶配对：

$$
e_{W^*; j}(e_{W; k}) = \langle e_{W^*; j}, e_{W; k} \rangle = (e_{W; j})^\mathrm{T} e_{W; k} = \delta_{j, k}
$$

---

#### **定义 1.2（集合张量空间与初等张量）**

定义集合张量空间为 $\mathcal{E}_{n,N} := V \otimes W^* = \mathbb{R}^n \otimes (\mathbb{R}^N)^*$。
初等基底张量定义为：
$$
E_{V, W^*; i, j} := e_{V; i} \otimes e_{W^*; j} \in \mathcal{E}_{n,N}
$$

---

#### **定理 1.1（集合张量的矩阵表示定理）**

任意集合张量 $\bm{X} \in \mathcal{E}_{n,N}$ 在基底 $\{E_{V, W^*; i, j}\}$ 下具有唯一的张量坐标展开：

$$
\bm{X} = \sum_{i=1}^n \sum_{j=1}^N X_{i, j} \, (e_{V; i} \otimes e_{W^*; j}) = \sum_{j=1}^N x_j \otimes e_{W^*; j}
$$

通过典范同构映射 $\Phi: \mathcal{E}_{n,N} \xrightarrow{\sim} \operatorname{Hom}(W, V) \cong M_{n,N}(\mathbb{R})$（在基底 $\{e_{V; i}\}$ 与 $\{e_{W^*; j}\}$ 下，初等张量 $E_{V, W^*; i, j}$ 典范对应于矩阵单位 $\bm{E}_{i, j} = e_{V; i} (e_{W; j})^\mathrm{T}$），集合张量 $\bm{X}$ 在基底下的表示矩阵记为 $[\bm{X}]_{e_V, e_{W^*}} = \Phi(\bm{X}) \in M_{n,N}(\mathbb{R})$：

$$
[\bm{X}]_{e_V, e_{W^*}} = \begin{pmatrix} X_{1, 1} & \cdots & X_{1, N} \\ \vdots & \ddots & \vdots \\ X_{n, 1} & \cdots & X_{n, N} \end{pmatrix} = (x_1, x_2, \dots, x_N)
$$

其中：

* $X_{i, j} \in \mathbb{R}$ 为表示矩阵 $[\bm{X}]_{e_V, e_{W^*}}$ 的第 $i$ 行第 $j$ 列元素。
* $x_j = \sum_{i=1}^n X_{i, j} e_{V; i} \in \mathbb{R}^n$ 为第 $j$ 个粒子的物理状态向量。

---

### **§2 张量算子 $(f \otimes g)$ 及其矩阵表示**

#### **定义 2.1（张量积算子）**

设线性映射 $f: \mathbb{R}^n \to \mathbb{R}^m$，对偶线性映射 $g: (\mathbb{R}^N)^* \to (\mathbb{R}^M)^*$\text{（即存在 $G \in M_{N,M}(\mathbb{R})$ 使得 $g(\alpha) = \alpha G$）}。
定义张量积算子 $(f \otimes g): \mathbb{R}^n \otimes (\mathbb{R}^N)^* \to \mathbb{R}^m \otimes (\mathbb{R}^M)^*$ 在初等单张量 $u \otimes \alpha$ 上的作用为：

$$
(f \otimes g)(u \otimes \alpha) := f(u) \otimes g(\alpha)
$$

---

#### **定理 2.1（$(f \otimes g)(\bm{X})$ 的三明治矩阵表示定理）**

设线性算子 $f: V \to V'$ 在基底下的矩阵为 $F = [f]_{e_{V'}, e_V} \in M_{m,n}(\mathbb{R})$（即 $f(u) = Fu$）；
设对偶算子 $g: W^* \to (W')^*$ 对应于样本空间算子 $G = [g]_{e_W, e_{W'}} \in M_{N,M}(\mathbb{R})$（即 $g(\alpha) = \alpha G$）。
设 $\bm{X} \in \mathcal{E}_{n,N}$ 的表示矩阵为 $[\bm{X}]_{e_V, e_{W^*}} \in M_{n,N}(\mathbb{R})$。
则张量算子作用后的集合张量 $(f \otimes g)(\bm{X})$ 在对应基底下的表示矩阵完全由**矩阵三明治乘法**给出：

$$
[(f \otimes g)(\bm{X})]_{e_{V'}, e_{(W')^*}} = F [\bm{X}]_{e_V, e_{W^*}} G \in M_{m,M}(\mathbb{R})
$$

*证明*：

1. 计算初等张量 $E_{V, W^*; i, j} = e_{V; i} \otimes e_{W^*; j}$ 在算子下的作用：

$$
(f \otimes g)(e_{V; i} \otimes e_{W^*; j}) = f(e_{V; i}) \otimes g(e_{W^*; j}) = (F e_{V; i}) \otimes (e_{W^*; j} G)
$$

2. 将初等张量取表示矩阵，注意 $[e_{V; i} \otimes e_{W^*; j}]_{e_V, e_{W^*}} = e_{V; i} (e_{W; j})^\mathrm{T} = \bm{E}_{i, j}$：

$$
[(f \otimes g)(E_{V, W^*; i, j})]_{e_{V'}, e_{(W')^*}} = (F e_{V; i}) (e_{W; j}^\mathrm{T} G) = F (e_{V; i} e_{W; j}^\mathrm{T}) G = F \bm{E}_{i, j} G
$$

3. 由线性性，对任意 $\bm{X} = \sum_{i,j} X_{i, j} E_{V, W^*; i, j}$：
$$
\begin{aligned}
[(f \otimes g)(\bm{X})]_{e_{V'}, e_{(W')^*}} &= \sum_{i,j} X_{i, j} [(f \otimes g)(E_{V, W^*; i, j})]_{e_{V'}, e_{(W')^*}} \\
&= \sum_{i,j} X_{i, j} F \bm{E}_{i, j} G = F \left( \sum_{i,j} X_{i, j} \bm{E}_{i, j} \right) G = F [\bm{X}]_{e_V, e_{W^*}} G \quad \blacksquare
\end{aligned}
$$

---

#### **推论 2.1（单侧物理算子与单侧统计算子）**

1. **纯物理算子（左乘）**：令 $g = \operatorname{id}_{W^*}$（对应 $G = \bm{I}_N$），则：

$$
[(f \otimes \operatorname{id})(\bm{X})]_{e_{V'}, e_{W^*}} = F [\bm{X}]_{e_V, e_{W^*}}
$$

2. **纯统计/变换算子（右乘）**：令 $f = \operatorname{id}_V$（对应 $F = \bm{I}_n$），则：

$$
[(\operatorname{id} \otimes g)(\bm{X})]_{e_V, e_{(W')^*}} = [\bm{X}]_{e_V, e_{W^*}} G
$$

---

#### **推论 2.2（向量化与 Kronecker 积表示）**

利用列向量化算子 $\operatorname{vec}: M_{n,N}(\mathbb{R}) \to \mathbb{R}^{nN}$，算子 $(f \otimes g)$ 对应的表示矩阵具有等价的 Kronecker 矩阵向量形式：

$$
\operatorname{vec}([(f \otimes g)(\bm{X})]_{e_{V'}, e_{(W')^*}}) = (G^\mathrm{T} \otimes F) \operatorname{vec}([\bm{X}]_{e_V, e_{W^*}})
$$

---

# §New! 态矢基底表示与张量积代数性质

设空间 $V$ 维数为 $m$，基矢行向量记为 $|e_{V; 1..m}\rangle = (|e_{V; 1}\rangle, \dots, |e_{V; m}\rangle)$；
设空间 $W$ 维数为 $n$，基矢行向量记为 $|e_{W; 1..n}\rangle = (|e_{W; 1}\rangle, \dots, |e_{W; n}\rangle)$。

任意态矢 $|x\rangle \in V$ 与 $|y\rangle \in W$ 在各自基底下的坐标列向量分别为 $\bm{x} \in \mathbb{C}^{m \times 1}$ 与 $\bm{y} \in \mathbb{C}^{n \times 1}$：
$$
|x\rangle = |e_{V; 1..m}\rangle \bm{x} = \sum_{i=1}^m x_i |e_{V; i}\rangle, \qquad |y\rangle = |e_{W; 1..n}\rangle \bm{y} = \sum_{j=1}^n y_j |e_{W; j}\rangle
$$

---
张量积空间 $V \otimes W$ 的维数为 $mn$，其标准基底由所有有序基矢对给出：
$$
\left\{ |e_{V; i} \otimes e_{W; j}\rangle \right\}_{i=1, \, j=1}^{m, \, n}
$$

对简单张量（Rank-1 张量）$|x \otimes y\rangle := |x\rangle \otimes |y\rangle$，利用双线性性质直接在积基底下展开：
$$
|x \otimes y\rangle = \left( \sum_{i=1}^m x_i |e_{V; i}\rangle \right) \otimes \left( \sum_{j=1}^n y_j |e_{W; j}\rangle \right) = \sum_{i=1}^m \sum_{j=1}^n x_i y_j \, |e_{V; i} \otimes e_{W; j}\rangle
$$
当然也可以写作
$$
|x \otimes y\rangle = (|e_{V; 1..m}\rangle \bm{x}) \otimes (|e_{W; 1..n}\rangle \bm{y}) = (|e_{V; 1..m}\rangle \otimes |e_{W; 1..n}\rangle) (\bm{x} \otimes \bm{y})
$$

* **几何基底算子：** $|e_{V; 1..m}\rangle \otimes |e_{W; 1..n}\rangle : \mathbb{C}^m \otimes \mathbb{C}^n \to V \otimes W$
* **数值坐标张量：** $\bm{x} \otimes \bm{y} \in \mathbb{C}^m \otimes \mathbb{C}^n$

---
设线性算子 $\mathscr{A} \in \mathcal{B}(V)$ 与 $\mathscr{B} \in \mathcal{B}(W)$ 的矩阵表示分别为 $\bm{A} = [\mathscr{A}]_{e_V} \in \mathbb{C}^{m \times m}$ 与 $\bm{B} = [\mathscr{B}]_{e_W} \in \mathbb{C}^{n \times n}$，满足：
$$
\mathscr{A}|e_{V; 1..m}\rangle = |e_{V; 1..m}\rangle \bm{A}, \qquad \mathscr{B}|e_{W; 1..n}\rangle = |e_{W; 1..n}\rangle \bm{B}
$$
根据一些交换代数关于t-prod的定义定理，存在唯一well-def的$$
(\mathscr{A} \otimes \mathscr{B}) |x \otimes y\rangle := |\mathscr{A}x\rangle \otimes |\mathscr{B}y\rangle
$$
计算有
$$
|\mathscr{A}x\rangle \otimes |\mathscr{B}y\rangle = \left( |e_{V; 1..m}\rangle (\bm{A}\bm{x}) \right) \otimes \left( |e_{W; 1..n}\rangle (\bm{B}\bm{y}) \right) = (|e_{V; 1..m}\rangle \otimes |e_{W; 1..n}\rangle) (\bm{A}\bm{x} \otimes \bm{B}\bm{y})
$$
以及更为基础的
$$
(\mathscr{A} \otimes \mathscr{B}) (|e_{V; 1..m}\rangle \otimes |e_{W; 1..n}\rangle)  = (|e_{V; 1..m}\rangle \otimes |e_{W; 1..n}\rangle) (\bm{A} \otimes \bm{B})
$$
于是
$$
\begin{aligned}
(\mathscr{A} \otimes \mathscr{B}) |x \otimes y\rangle &= (\mathscr{A} \otimes \mathscr{B}) \left[ (|e_{V; 1..m}\rangle \otimes |e_{W; 1..n}\rangle) (\bm{x} \otimes \bm{y}) \right] \\
&= \left[ (\mathscr{A} \otimes \mathscr{B}) (|e_{V; 1..m}\rangle \otimes |e_{W; 1..n}\rangle) \right] (\bm{x} \otimes \bm{y})\\
&= \left[ (|e_{V; 1..m}\rangle \otimes |e_{W; 1..n}\rangle) (\bm{A} \otimes \bm{B}) \right] (\bm{x} \otimes \bm{y})
\end{aligned}
$$

当然，注意到 $(\bm{A} \otimes \bm{B}) (\bm{x} \otimes \bm{y}) = \bm{A}\bm{x} \otimes \bm{B}\bm{y} = \bm{A}\bm{x} \bm{y}^{\mathrm{T}}\bm{B}^{\mathrm{T}}$

---
张量的复合性质:
$$
\begin{aligned}
&\bigl[(\mathscr A_1\otimes_t\mathscr B_1)
\circ(\mathscr A_2\otimes_t\mathscr B_2)\bigr]
\bigl(|e_{V;1..n}\rangle\otimes_t|e_{W;1..m}\rangle\bigr)
\\
&=(\mathscr A_1\otimes_t\mathscr B_1)
\bigl((\mathscr A_2|e_{V;1..n}\rangle)
\otimes_t(\mathscr B_2|e_{W;1..m}\rangle)\bigr)
\\
&=(\mathscr A_1\otimes_t\mathscr B_1)
\bigl((|e_{V;1..n}\rangle\bm A_2)
\otimes_t(|e_{W;1..m}\rangle\bm B_2)\bigr)
\\
&=\bigl((\mathscr A_1|e_{V;1..n}\rangle)\bm A_2\bigr)
\otimes_t
\bigl((\mathscr B_1|e_{W;1..m}\rangle)\bm B_2\bigr)
\\
&=(|e_{V;1..n}\rangle\bm A_1\bm A_2)
\otimes_t
(|e_{W;1..m}\rangle\bm B_1\bm B_2)
\\
&=\bigl((\mathscr A_1\circ\mathscr A_2)|e_{V;1..n}\rangle\bigr)
\otimes_t
\bigl((\mathscr B_1\circ\mathscr B_2)|e_{W;1..m}\rangle\bigr)
\\
&=\bigl[(\mathscr A_1\circ\mathscr A_2)
\otimes_t(\mathscr B_1\circ\mathscr B_2)\bigr]
\bigl(|e_{V;1..n}\rangle\otimes_t|e_{W;1..m}\rangle\bigr).
\end{aligned}
$$

/* 
我想到 $|e_{V;1..n}\rangle\otimes_t|e_{W;1..m}\rangle$ 和 $|e_{V;1..n}\otimes_t e_{W;1..m}\rangle$ 的关系，不确定。而且最后一步是否还可以进一步写为 $|e_{V;1..n}\otimes_t e_{W;1..m}\rangle (\bm{A}_1 \bm{A}_2) \otimes (\bm{B}_1 \bm{B}_2)$ ? 

此外，$\mathscr{A}e_{1..n} = \mathscr{A} \circ e = \Phi (\sum_{j = 1:n} \mathscr{A}e_j \otimes \bm{1}_{j}) = [\mathscr{A}e_1, \cdots, \mathscr{A}e_n]$ 我也尚未书写

还有就是对于内积空间 $\mathcal{H}$, 选取其标准正交基 $e_{1..n}$. 然后 $[\mathscr{A}]_{e_{1..n}} = \langle e_{1..n}|\mathscr{A}|e_{1..n} \rangle$. 由此受到启发计算有 
$$
\begin{aligned}
&[\mathscr{A} \otimes \mathscr{B}]_{e_V\otimes e_W} = \langle e_V\otimes e_W|\mathscr{A} \otimes \mathscr{B}|e_V\otimes e_W \rangle = \langle e_V\otimes e_W|\mathscr{A} e_V\otimes \mathscr{B}e_W \rangle 
\\ =& \langle e_V\otimes e_W|e_V\bm{A}\otimes e_W\bm{B} \rangle = \langle e_V\otimes e_W|(e_V\otimes e_W)\circ (\bm{A} \otimes \bm{B}) \rangle
\\ =& \langle e_V\otimes e_W|(e_V\otimes e_W) \rangle \circ (\bm{A} \otimes_t \bm{B}) = \bm{A} \otimes_t \bm{B}
\end{aligned}
$$
所以要讨论 $\bm{A} \otimes_t \bm{B}$ 和 $\bm{A} \otimes_k \bm{B}$ 的关系。

我察觉到，此时，就必须涉及到用index来考虑。实际上GPT给出了一个漂亮的计算，定义$$
\mathrm{T}_{i\alpha j\beta} := \langle e_{V;i} \otimes e_{W;\alpha} | \mathrm{T} | e_{V;j} \otimes e_{W;\beta} \rangle
$$
计算有
$$
\begin{aligned}
& (\mathscr{A} e_{V;j}) \otimes (\mathscr{B} e_{W;\beta}) = \sum_{p,q} A_{pj} B_{q\beta} \, e_{V;p} \otimes e_{W;q} \\
\Longrightarrow & \langle e_{V;i} \otimes e_{W;\alpha} | \mathscr{A} e_{V;j} \otimes \mathscr{B} e_{W;\beta} \rangle = \sum_{p,q} A_{pj} B_{q\beta} \delta_{ip} \delta_{\alpha q} = A_{ij} B_{\alpha\beta}.
\end{aligned}
$$
这样就获得index $(\bm{A} \otimes_t \bm{B})_{i\alpha j\beta} := A_{ij} B_{\alpha\beta}$, 不管是 $\bm{A} \otimes_t \bm{B}$ 还是 $\bm{A} \otimes_k \bm{B}$，其分量总是一致的。

嗯，考虑 $\mathscr{A}(e_{V;j}) = \sum_i A_{ij} e_{W;i}$，我学习到了线性映射index的输入和输出的区分，$(i,j)$ 中，作用向量 $e_{V;j}$ 就是输入basis, 而 $e_{W;i}$ 则是输出basis. 很神奇
*/

要证明 $(\mathscr{A}_1 \otimes \mathscr{B}_1) \circ (\mathscr{A}_2 \otimes \mathscr{B}_2) = (\mathscr{A}_1 \circ \mathscr{A}_2) \otimes (\mathscr{B}_1 \circ \mathscr{B}_2)$ 还可以直接在简单张量上验证：
$$
\begin{aligned}
&((\mathscr{A}_1 \otimes \mathscr{B}_1) \circ (\mathscr{A}_2 \otimes \mathscr{B}_2))(x \otimes y) \\
&= \mathscr{A}_1\mathscr{A}_2 x \otimes \mathscr{B}_1\mathscr{B}_2 y \\
&= ((\mathscr{A}_1 \circ \mathscr{A}_2) \otimes (\mathscr{B}_1 \circ \mathscr{B}_2))(x \otimes y).
\end{aligned}
$$