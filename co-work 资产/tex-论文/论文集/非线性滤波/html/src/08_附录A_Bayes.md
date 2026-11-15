# Bayes 滤波引理与更新公式证明 {#cw:app:appendix}

## 无记忆性引理的离散情形证明 {#cw:app:markov-proof}

::: 证明 {@cw:lem:markov} 的证明（离散情形）

沿用{@cw:lem:markov} 的模型与独立性条件，设 $X_0$ 和各噪声取有限或可数个值，$p$ 表示相对于计数测度的概率质量函数。
以下仅考虑概率为正的条件取值，求和遍历相应噪声的所有可能取值。

由递推关系，$(X_{0:k-1},Y_{1:k-1})$ 是 $(X_0,N_{x,1:k-1},N_{y,1:k-1})$ 的函数，因此与 $N_{x,k}$ 独立。
固定历史取值后，$X_{k-1}=x_{k-1}$，先按噪声取值分解，再依次使用 $X_k=f(X_{k-1},N_{x,k})$ 与噪声独立性：

$$
\begin{aligned}
&p_{X_k\mid X_{0:k-1},Y_{1:k-1}}(x_k\mid x_{0:k-1},y_{1:k-1})\\
= &\sum_n p_{(X_k,N_{x,k})\mid X_{0:k-1},Y_{1:k-1}}(x_k,n\mid x_{0:k-1},y_{1:k-1})\\
= &\sum_n\mathbb I_{\{f(x_{k-1},n)=x_k\}}p_{N_{x,k}\mid X_{0:k-1},Y_{1:k-1}}(n\mid x_{0:k-1},y_{1:k-1})\\
= &\sum_n\mathbb I_{\{f(x_{k-1},n)=x_k\}}p_{N_{x,k}}(n)\\
= &p_{X_k\mid X_{k-1}}(x_k\mid x_{k-1}).
\end{aligned}
$$

最后一步同样利用 $N_{x,k}$ 与 $X_{k-1}$ 独立，故只给定 $X_{k-1}$ 时得到相同的求和式。

同理，$(X_{0:k},Y_{1:k-1})$ 是 $(X_0,N_{x,1:k},N_{y,1:k-1})$ 的函数，因此与 $N_{y,k}$ 独立。由 $Y_k=h(X_k,N_{y,k})$ 得

$$
\begin{aligned}
&p_{Y_k\mid X_{0:k},Y_{1:k-1}}(y_k\mid x_{0:k},y_{1:k-1})\\
= &\sum_n\mathbb I_{\{h(x_k,n)=y_k\}}p_{N_{y,k}}(n)\\
= &p_{Y_k\mid X_k}(y_k\mid x_k).
\end{aligned}
$$

这里最后一步利用 $N_{y,k}$ 与 $X_k$ 独立。$k=1$ 时将历史观测视为空，即得引理的两个等式。

一般情形对任意可测集合写条件概率，将上述求和替换为对噪声分布的积分，即得相同的条件分布等式；在正文的密度存在假设下，进一步得到几乎处处成立的密度等式。

:::

## Bayes 更新公式的证明 {#cw:app:proofs}

::: 定理 {#cw:thm:bayes} Bayes 更新公式

在本文约定与模型条件下，对 $k\geq1$，给定历史观测 $y_{1:k-1}$ 并收到当前观测 $y_k$ 后，状态后验密度满足

$$ {#cw:eq:15}
\begin{aligned}
&p_{X_k\mid Y_{1:k}}(x_k\mid y_{1:k})\\
= &\frac{p_{Y_k\mid X_k}(y_k\mid x_k)p_{X_k\mid Y_{1:k-1}}(x_k\mid y_{1:k-1})}
{\displaystyle\int_{\mathcal{S}_X}p_{Y_k\mid X_k}(y_k\mid x)p_{X_k\mid Y_{1:k-1}}(x\mid y_{1:k-1})\,\mathrm{d}v_X(x)}.
\end{aligned}
$$

:::

::: 证明

经典结论参见文献[@sarkka2013bayesian,cappe2005inference]；为完整起见，下面给出自行推导的证明。

先固定历史观测 $y_{1:k-1}$。收到 $y_k$ 后，要求的是在这些历史观测的基础上，再给定 $Y_k=y_k$ 时的状态密度。按条件密度公式，将条件联合密度除以新观测的条件边缘密度：

$$ {#cw:eq:16}
\begin{aligned}
&p_{X_k\mid Y_{1:k}}(x_k\mid y_{1:k})\\
= &\frac{p_{(X_k,Y_k)\mid Y_{1:k-1}}(x_k,y_k\mid y_{1:k-1})}
{p_{Y_k\mid Y_{1:k-1}}(y_k\mid y_{1:k-1})}.
\end{aligned}
$$

对分子使用密度的乘法公式，按“先取状态，再给定状态取观测”的顺序分解。两个因子都保留历史观测条件，其中状态因子正是预测步骤已求得的密度：

$$ {#cw:eq:17}
\begin{aligned}
&p_{(X_k,Y_k)\mid Y_{1:k-1}}(x_k,y_k\mid y_{1:k-1})\\
= &p_{Y_k\mid X_k,Y_{1:k-1}}(y_k\mid x_k,y_{1:k-1})
p_{X_k\mid Y_{1:k-1}}(x_k\mid y_{1:k-1}).
\end{aligned}
$$

将这一分解代入上一式，就是以历史观测为条件的 Bayes 公式。

接着应用无记忆性引理中的观测条件独立性。给定当前状态 $X_k$ 后，历史观测不再影响 $Y_k$ 的条件分布，因此观测因子可以直接使用模型给出的似然：

$$ {#cw:eq:18}
p_{Y_k\mid X_k,Y_{1:k-1}}(y_k\mid x_k,y_{1:k-1})
=p_{Y_k\mid X_k}(y_k\mid x_k).
$$

这里仅消去了观测因子中的历史条件，预测密度仍依赖历史观测。

分母由条件联合密度对状态变量积分得到，这是条件全概率公式。再代入上面的乘法分解与条件独立关系，就将观测的预测密度写成似然关于状态预测分布的平均：

$$ {#cw:eq:19}
\begin{aligned}
&p_{Y_k\mid Y_{1:k-1}}(y_k\mid y_{1:k-1})\\
= &\int_{\mathcal{S}_X}p_{(X_k,Y_k)\mid Y_{1:k-1}}(x,y_k\mid y_{1:k-1})\,\mathrm{d}v_X(x)\\
= &\int_{\mathcal{S}_X}p_{Y_k\mid X_k}(y_k\mid x)
p_{X_k\mid Y_{1:k-1}}(x\mid y_{1:k-1})\,\mathrm{d}v_X(x).
\end{aligned}
$$

其中 $x$ 是积分变量，覆盖整个状态空间。按前述条件，这个分母有限且严格为正，可以用于归一化。

最后，将得到的分子与分母代回最初的条件密度公式，即得定理中的更新式。分母是似然加权后预测密度的总积分，因此相除后得到积分为 $1$ 的后验密度。

:::
