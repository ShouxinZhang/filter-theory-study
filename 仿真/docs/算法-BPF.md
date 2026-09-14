# BPF: Bootstrap Particle Filter

依据 [Gordon 1993](https://people.bordeaux.inria.fr/pierre.delmoral/gordon-salmond-smith-1993.pdf) 第 3.1 节与 [仓库 BPF 笔记](../../粒子滤波/bpf-basic.md)。
完整输入输出遵守 [公共接口](接口-在线滤波.md); 输入模型, 初始先验, $N$, 随机流与当前观测 $y_k$, 返回当前 `FilterStep`。
采用转移先验作为提议分布; 预测与似然归一化完全使用公共接口, 每步重采样。
给定当前预测粒子与归一化权重, 条件独立地抽取祖先索引, 并复制对应位置:
$$
\begin{aligned}
&A_k^{(j)}\mid\bm w_k^+\sim\operatorname{Categorical}(w_k^{+,(1)},\dots,w_k^{+,(N)}),\;j=1,\dots,N,\\
&x_k^{+,(j)}=x_k^{-,(A_k^{(j)})},\;w_{k,\mathrm{next}}^{(j)}=\frac1N,\\
&\widetilde{\mathbb P}_{N;X_k}^+=\frac1N\sum_{j=1}^N\delta_{x_k^{+,(j)}}.
\end{aligned}
$$
实现采用独立均匀随机数与权重累积分布的逆变换, 即多项式重采样; 它不同于系统重采样或分层重采样。
正态噪声要求针对物理过程与观测; 重采样的均匀数是算法随机性, 不属于环境噪声。
主输出均值 $\hat x_k=\sum_iw_k^{+,(i)}x_k^{-,(i)}$, 同时输出等权集合供递推和重采样诊断。
重采样后的样本均值一般不严格等于 $\hat x_k$, 只在给定预测集合与权重后对重采样随机性取期望时相等。
以累积分布加二分查找实现时, 重采样为 $O(N\log N)$, 工作存储为 $O(Nn_x)$; 模型传播与似然求值另计。
