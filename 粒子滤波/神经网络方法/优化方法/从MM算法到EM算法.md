# 从 MM 算法到 EM 算法

MM（Minorize–Maximization）算法通过构造目标函数的切触次化下界并迭代最大化，保证目标函数单调上升。

在含隐变量 $X$ 的统计参数估计中，把参数视为随机变量 $\bm{\Theta}$，从条件分布 $\mathbb P_{Y\mid\bm{\Theta}}$ 出发，观测 $y$ 的似然为 $L(\bm{\theta})=p_{Y\mid\bm{\Theta}}(y\mid\bm{\theta})=\int_{\mathcal X} p_{(X,Y)\mid\bm{\Theta}}(x,y\mid\bm{\theta})\,\mathrm{d}v(x)$。
极大似然估计 $\hat{\bm{\theta}}\in\arg\max_{\bm{\theta}\in\mathcal T}L(\bm{\theta})=\arg\max_{\bm{\theta}\in\mathcal T}f(\bm{\theta})$，其中 $f(\bm{\theta}):=\log L(\bm{\theta})$，因 $\log$ 严格单调，两者最大点相同。

对状态变换 $X\mapsto T(X)$（$T$ 为可测映射），记 $\tilde{X}:=T(X)$，其分布为推前 $\mathbb P_{\tilde{X}}=T_*\mathbb P_X$，密度为 $p_{\tilde{X}}(\tilde{x})=\frac{\mathrm d\mathbb P_{\tilde{X}}}{\mathrm dv}(\tilde{x})$，自由能为
$$\mathcal F(T(X),\bm{\theta}):=\int_{\mathcal X}p_{\tilde{X}}(\tilde{x})\log\frac{p_{(X,Y)\mid\bm{\Theta}}(\tilde{x},y\mid\bm{\theta})}{p_{\tilde{X}}(\tilde{x})}\,\mathrm{d}v(\tilde{x})=f(\bm{\theta})-D_{\mathrm{KL}}(\mathbb P_{\tilde{X}}\,\|\,\mathbb P_{X\mid(Y,\bm{\Theta})=(y,\bm{\theta})})\le f(\bm{\theta}).$$

E 步（Minorize）：间隙 $f(\bm{\theta})-\mathcal F(T(X),\bm{\theta})=D_{\mathrm{KL}}(\mathbb P_{\tilde{X}}\,\|\,\mathbb P_{X\mid(Y,\bm{\Theta})=(y,\bm{\theta})})$ 在 $\bm{\theta}=\bm{\theta}^{(t)}$ 处为 $0$，当且仅当 $\mathbb P_{\tilde{X}}=\mathbb P_{X\mid(Y,\bm{\Theta})=(y,\bm{\theta}^{(t)})}$，即选取 $T^{(t)}$ 使 $T^{(t)}_*\mathbb P_X=\mathbb P_{X\mid(Y,\bm{\Theta})=(y,\bm{\theta}^{(t)})}$（把先验 $\mathbb P_X$ 输运到当前后验）。此时 $g(\bm{\theta}\mid\bm{\theta}^{(t)}):=\mathcal F(T^{(t)}(X),\bm{\theta})$ 满足全局下界与锚点相切，故 $T$ 由 E 步确定。

M 步（Maximize）：固定 $T^{(t)}$，更新 $\bm{\theta}^{(t+1)}\in\arg\max_{\bm{\theta}\in\mathcal T}\mathcal F(T^{(t)}(X),\bm{\theta})$，恰为 EM 算法的 M 步。

具体推导、KL 散度残余分析与单调性证明可参见 [优化方法.md](优化方法.md)。
