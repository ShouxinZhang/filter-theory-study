# ETPF: Ensemble Transform Particle Filter

依据 [Reich 2013](https://arxiv.org/abs/1210.0375), 矩阵符号与方向沿用 [OTPF](../../otpf-basic.md), 本基线使用无熵正则的原始输运目标。
完整输入输出遵守 [公共接口](接口-在线滤波.md); 额外输入输运求解器配置, 返回 `FilterStep` 与求解状态, 边际残差和目标值。
初始化, 传播和似然加权与 BPF 相同; 每次加权后通过确定性重心变换得到等权集合。
给定预测粒子与 $\bm w_k^+$, 第 $i$ 行对应加权源粒子, 第 $j$ 列对应等权预测参考位置:
$$
\begin{aligned}
&(\bm C_k)_{ij}=\|x_k^{-,(i)}-x_k^{-,(j)}\|_{\mathbb R^{n_x}}^2,\\
&\bm\Pi_k\in\operatorname*{arg\,min}_{\bm\Pi\ge0}\sum_{i=1}^N\sum_{j=1}^N\Pi_{ij}(\bm C_k)_{ij},\\
&\bm\Pi\mathbf1_N=\bm w_k^+,\;\bm\Pi^{\mathrm T}\mathbf1_N=\frac1N\mathbf1_N,\\
&\bm T_k=N\bm\Pi_k,\;x_k^{+,(j)}=\sum_{i=1}^N(\bm T_k)_{ij}x_k^{-,(i)},\;X_k^+=X_k^-\bm T_k.
\end{aligned}
$$
参考位置定义输运代价, 输出粒子是源粒子的列重心, 通常不等于参考位置。
输出等权分布 $\widetilde{\mathbb P}_{N;X_k}^+=N^{-1}\sum_j\delta_{x_k^{+,(j)}}$, 并保留公共接口定义的加权后验。
精确边际约束保证均值守恒:
$$
\frac1N\sum_{j=1}^Nx_k^{+,(j)}=\sum_{i=1}^Nw_k^{+,(i)}x_k^{-,(i)}=\hat x_k.
$$
有限 $N$ 时重心变换通常改变协方差, 不保证精确保持完整后验分布或二阶矩。
一维平方代价使用排序后的单调质量匹配, 排序 $O(N\log N)$, 匹配 $O(N)$, 相同位置按原编号打破排序平局。
四维使用无正则输运线性规划; 默认平方欧氏代价直接使用环境原始坐标, 不进行逐步标准化。
固定求解器版本, 确定性选解规则及容差; 记录行列边际最大绝对残差, 非负性违背量与最优性间隙, 未达声明容差则标记失败。
多维稠密代价需要 $O(N^2)$ 存储, 求解耗时计入滤波计时; 不将其复杂度视为一维排序复杂度。
Sinkhorn 的 $\varepsilon>0$ 熵正则形式属于单独的 `ETPF-Sinkhorn` 变体, 不能与本基线混用。
