# preset
沿用 [非线性滤波问题.md](粒子滤波/非线性滤波问题.md) 中的定义, $N$ 为粒子数, $-,+$ 分别表示预测与后验阶段。固定本轮预测粒子 $x_k^{-,(i)}\in\mathbb R^{n_x\times1}$ 及当前观测 $y_k$, 预测经验测度为
$$
\hat{\mathbb P}_{N;X_k}^-:=\frac1N\sum_{i=1}^N\delta_{x_k^{-,(i)}}.
$$
对任意可测集合 $A\subseteq\mathcal X$, 将预测经验测度代入 Bayes 更新, 定义
$$
\begin{aligned}
&\hat{\mathbb P}_{N;X_k}^+(A):=\frac{\displaystyle\int_A p(y_k\mid x)\,\mathrm d\hat{\mathbb P}_{N;X_k}^-(x)}{\displaystyle\int_{\mathcal X}p(y_k\mid x)\,\mathrm d\hat{\mathbb P}_{N;X_k}^-(x)}\\
= &\sum_{i=1}^Nw_k^{+,(i)}\delta_{x_k^{-,(i)}}(A),\\
&w_k^{+,(i)}:=\frac{p(y_k\mid x_k^{-,(i)})}{\displaystyle\sum_{r=1}^Np(y_k\mid x_k^{-,(r)})},\;i=1,\dots,N.
\end{aligned}
$$
这里 $p(y_k\mid x)=p_{Y_k\mid X_k}(y_k\mid x)$, 假设粒子似然总和有限且严格为正。将所得权重排列为 $\bm w_k^+=(w_k^{+,(1)},\dots,w_k^{+,(N)})^{\mathrm T}\in\Delta^{N-1}$。
这一步只更新了权重, 粒子位置仍为 $x_k^{-,(i)}$。下面希望用新的等权粒子 $x_k^{+,(j)}$ 表示后验近似, 以便进入下一轮预测。

---
# main
沿用离散输运中的边际记号 $\bm a,\bm b$, 当前时刻的代价矩阵记为 $\bm C_k\in\mathbb R^{N\times N}$, 令
$$
\begin{aligned}
&\bm a=\bm w_k^+,\;\bm b=\frac1N\mathbf1_N,\;(\bm C_k)_{ij}:=\|x_k^{-,(i)}-x_k^{-,(j)}\|^2,\\
&\bm\Pi_k\in U(\bm a,\bm b),\;\bm\Pi_k\mathbf1_N=\bm w_k^+,\;\bm\Pi_k^{\mathrm T}\mathbf1_N=\frac1N\mathbf1_N.
\end{aligned}
$$
这里 $i,j=1,\dots,N$, 第 $i$ 行对应后验权重为 $w_k^{+,(i)}$ 的预测粒子, 第 $j$ 列对应等权的目标参考位置 $x_k^{-,(j)}$。源边际为加权后验经验测度, 目标边际为等权预测经验测度。将 $\bm a,\bm b,\bm C_k$ 代入 [ot-sinkhorn.md](ot-sinkhorn.md) 的熵正则化目标, 用 Sinkhorn 求解 $\bm\Pi_k$；正则化参数 $\varepsilon$ 保留在求解目标中。

位置变换矩阵 $\bm T_k\in\mathbb R^{N\times N}$ 为
$$
\begin{aligned}
&(\bm T_k)_{ji}:=N(\bm\Pi_k)_{ij},\;\bm T_k=N\bm\Pi_k^{\mathrm T},\\
&\bm T_k\mathbf1_N=\mathbf1_N,\;\bm T_k^{\mathrm T}\mathbf1_N=N\bm w_k^+.
\end{aligned}
$$
每行的变换系数非负且和为 $1$, 据此取源粒子的加权平均, 得到新粒子：
$$
\begin{aligned}
&x_k^{+,(j)}:=\sum_{i=1}^N(\bm T_k)_{ji}x_k^{-,(i)}=N\sum_{i=1}^N(\bm\Pi_k)_{ij}x_k^{-,(i)},\\
&\bm X_k^+=\bm X_k^-\bm T_k^{\mathrm T}=N\bm X_k^-\bm\Pi_k.
\end{aligned}
$$
