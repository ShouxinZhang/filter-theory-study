# 从 MM 算法到 EM 算法

MM（Minorize–Maximization）算法通过构造目标函数的切触次化下界并迭代最大化，保证目标函数单调上升。

在含隐变量 $X$ 的统计参数估计中，把参数视为随机变量 $\bm{\Theta}$，从条件分布 $\mathbb P_{Y\mid\bm{\Theta}}$ 出发，观测 $y$ 的似然为 $L(\bm{\theta})=p_{Y\mid\bm{\Theta}}(y\mid\bm{\theta})=\int_{\mathcal X} p_{(X,Y)\mid\bm{\Theta}}(x,y\mid\bm{\theta})\,\mathrm{d}v(x)$。
极大似然估计 $\hat{\bm{\theta}}\in\arg\max_{\bm{\theta}\in\mathcal T}L(\bm{\theta})=\arg\max_{\bm{\theta}\in\mathcal T}f(\bm{\theta})$，其中 $f(\bm{\theta}):=\log L(\bm{\theta})$，因 $\log$ 严格单调，两者最大点相同。

对状态变换 $X\mapsto T(X)$（$T$ 为可测映射），记 $\tilde{X}:=T(X)$，其分布为推前 $\mathbb P_{\tilde{X}}=T_*\mathbb P_X$，密度为 $p_{\tilde{X}}(\tilde{x})=\frac{\mathrm d\mathbb P_{\tilde{X}}}{\mathrm dv}(\tilde{x})$，自由能为
$$\mathcal F(T(X),\bm{\theta}):=\int_{\mathcal X}p_{\tilde{X}}(\tilde{x})\log\frac{p_{(X,Y)\mid\bm{\Theta}}(\tilde{x},y\mid\bm{\theta})}{p_{\tilde{X}}(\tilde{x})}\,\mathrm{d}v(\tilde{x})=f(\bm{\theta})-D_{\mathrm{KL}}(\mathbb P_{\tilde{X}}\,\|\,\mathbb P_{X\mid(Y,\bm{\Theta})=(y,\bm{\theta})})\le f(\bm{\theta}).$$

E 步（Minorize）：间隙 $f(\bm{\theta})-\mathcal F(T(X),\bm{\theta})=D_{\mathrm{KL}}(\mathbb P_{\tilde{X}}\,\|\,\mathbb P_{X\mid(Y,\bm{\Theta})=(y,\bm{\theta})})$ 在 $\bm{\theta}=\bm{\theta}^{(t)}$ 处为 $0$，当且仅当 $\mathbb P_{\tilde{X}}=\mathbb P_{X\mid(Y,\bm{\Theta})=(y,\bm{\theta}^{(t)})}$，即选取 $T^{(t)}$ 使 $T^{(t)}_*\mathbb P_X=\mathbb P_{X\mid(Y,\bm{\Theta})=(y,\bm{\theta}^{(t)})}$（把先验 $\mathbb P_X$ 输运到当前后验）。此时 $g(\bm{\theta}\mid\bm{\theta}^{(t)}):=\mathcal F(T^{(t)}(X),\bm{\theta})$ 满足全局下界与锚点相切，故 $T$ 由 E 步确定。

M 步（Maximize）：固定 $T^{(t)}$，更新 $\bm{\theta}^{(t+1)}\in\arg\max_{\bm{\theta}\in\mathcal T}\mathcal F(T^{(t)}(X),\bm{\theta})$，恰为 EM 算法的 M 步。

具体推导、KL 散度残余分析与单调性证明可参见 [优化方法.md](优化方法.md)。

## 算例：两枚硬币

一枚硬币正面概率为 $\theta\in\mathcal T=[0,1]$，另一枚为均匀硬币。连续抛 $n$ 次，每次先以概率 $\frac12$ 随机选一枚再抛，不记录选了哪枚。记 $B_k\in\{0,1\}$ 表示第 $k$ 次是否正面，$Y_k=\sum_{i=1}^{k}B_k$ 为前 $k$ 次的正面次数，观测 $Y_{1..n}$（由 $B_k=Y_k-Y_{k-1}$ 知等价于观测每次结果）。
隐变量取 $X=X_{1..n}$，其中 $X_k\in\{0,1\}$ 表示第 $k$ 次选了 $\theta$ 硬币。

单次正面概率：对隐变量 $X_k$ 求和（离散情形下 $v$ 为计数测度）。其含义为全概率公式：事件 $\{B_k=1\}$ 按硬币选择 $X_k$ 划分为两个互不相交的事件，各自的概率等于该硬币被选中的概率与其出现正面的条件概率之积，二者之和即为 $\{B_k=1\}$ 的概率，
$$\begin{aligned}
&\mathbb P_{B_k\mid\bm{\Theta}}(\{1\}\mid\theta)=\sum_{x_k\in\{0,1\}}\mathbb P_{X_k}(\{x_k\})\,\mathbb P_{B_k\mid(X_k,\bm{\Theta})}(\{1\}\mid x_k,\theta)\\
=&\frac12\cdot\theta+\frac12\cdot\frac12=\frac{\theta}{2}+\frac14=:q(\theta).
\end{aligned}$$

似然：由 $b_k=y_k-y_{k-1}$（$y_0=0$）知观测 $y_{1..n}$ 等价于 $b_{1..n}$。各次 $(X_k,B_k)$ 独立，对 $x_{1..n}\in\{0,1\}^n$ 求和可逐次分解，
$$\begin{aligned}
&L(\theta)=p_{Y_{1..n}\mid\bm{\Theta}}(y_{1..n}\mid\theta)=\sum_{x_{1..n}}\prod_{k=1}^{n}\mathbb P_{X_k}(\{x_k\})\,\mathbb P_{B_k\mid(X_k,\bm{\Theta})}(\{b_k\}\mid x_k,\theta)\\
=&\prod_{k=1}^{n}q(\theta)^{b_k}(1-q(\theta))^{1-b_k}=q(\theta)^{y_n}(1-q(\theta))^{n-y_n}.
\end{aligned}$$
$L$ 通过 $\sum_kb_k=y_n$ 只依赖正面总次数，各次的位置不影响似然。

极大似然：取 $f(\theta)=\log L(\theta)=y_n\log q(\theta)+(n-y_n)\log(1-q(\theta))$，$f$ 关于 $\theta$ 凹，令 $f'(\theta)=\frac12\bigl(\frac{y_n}{q}-\frac{n-y_n}{1-q}\bigr)=0$ 得 $q=\frac{y_n}{n}$，再限制到 $\mathcal T=[0,1]$，
$$\hat\theta=\min\Bigl\{1,\max\Bigl\{0,\frac{2y_n}{n}-\frac12\Bigr\}\Bigr\}.$$

E 步：后验下 $X_{1..n}$ 条件独立，且 $X_k$ 只依赖 $b_k$。由 Bayes 公式，$\mathbb P_{X_k\mid(B_k,\bm{\Theta})}(\{1\}\mid b_k,\theta^{(t)})=\frac{\mathbb P_{X_k}(\{1\})\,\mathbb P_{B_k\mid(X_k,\bm{\Theta})}(\{b_k\}\mid 1,\theta^{(t)})}{\mathbb P_{B_k\mid\bm{\Theta}}(\{b_k\}\mid\theta^{(t)})}$，取 $b_k=1,0$ 得
$$\mathbb P_{X_k\mid B_k}(\{1\}\mid 1,\theta^{(t)})=\frac{2\theta^{(t)}}{2\theta^{(t)}+1}=:a_1^{(t)},\qquad\mathbb P_{X_k\mid B_k}(\{1\}\mid 0,\theta^{(t)})=\frac{2(1-\theta^{(t)})}{3-2\theta^{(t)}}=:a_0^{(t)}.$$
M 步：完全数据对数似然的期望最大化给出 $\theta$ 硬币的期望正面次数与期望抛掷次数之比
$$\theta^{(t+1)}=\frac{y_na_1^{(t)}}{y_na_1^{(t)}+(n-y_n)a_0^{(t)}}.$$
不动点 $\theta=\theta^{(t)}$ 满足 $(n-y_n)(2\theta+1)=y_n(3-2\theta)$，即 $\theta=\frac{2y_n}{n}-\frac12$，与极大似然估计一致。
