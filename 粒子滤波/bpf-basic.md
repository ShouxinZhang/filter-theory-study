### 随机变量形式的非线性状态空间模型

设 $X_k, Y_k, N_{x,k}, N_{y,k}$ 为定义在概率空间 $(\Omega, \mathcal{F}, P)$ 上的随机变量（向量）：

$$
X_k = f(X_{k-1}, N_{x,k})
$$

$$
Y_k = h(X_k, N_{y,k})
$$

其中 $N_{x,k} \sim p_{N_x}$ 与 $N_{y,k} \sim p_{N_y}$ 分别为独立的过程噪声与观测噪声随机变量。

概率转移密度与观测似然的测度表达：

$$
p(X_k \mid X_{k-1}) = \int \delta\big(X_k - f(X_{k-1}, N_{x,k})\big) \, p_{N_x}(N_{x,k}) \, dN_{x,k}
$$

$$
p(Y_k \mid X_k) = \int \delta\big(Y_k - h(X_k, N_{y,k})\big) \, p_{N_y}(N_{y,k}) \, dN_{y,k}
$$

### 1. 连续贝叶斯滤波算子

预测（Chapman-Kolmogorov 方程）与更新（Bayes 法则）：

$$
p(x_k \mid y_{1:k-1}) = \int p(x_k \mid x_{k-1}) \, p(x_{k-1} \mid y_{1:k-1}) \, dx_{k-1}
$$

$$
p(x_k \mid y_{1:k}) \propto p(y_k \mid x_k) \, p(x_k \mid y_{1:k-1})
$$

### 2. 代入 Dirac 经验测度

假设上一时刻的后验分布直接用经验测度替代：

$$
p(x_{k-1} \mid y_{1:k-1}) \approx \frac{1}{N} \sum_{i=1}^N \delta_{x_{k-1}^{(i)}}(x_{k-1})
$$

**代入预测方程**（积分因 Dirac 函数退化为有限项混合分布）：

$$
p(x_k \mid y_{1:k-1}) \approx \int p(x_k \mid x_{k-1}) \left( \frac{1}{N} \sum_{i=1}^N \delta_{x_{k-1}^{(i)}}(x_{k-1}) \right) dx_{k-1} = \frac{1}{N} \sum_{i=1}^N p(x_k \mid x_{k-1}^{(i)})
$$

**分层采样（Stratified Sampling）步骤**：为对该混合分布进行 Monte Carlo 散化，对每个混合成分（层） $i \in \{1, \dots, N\}$ 分配 1 个样本，独立抽取预测粒子：

$$
x_k^{-,(i)} \sim p\left(x_k \mid x_{k-1}^{+,(i)}\right), \quad i = 1, \dots, N
$$

由此得到预测分布的先验经验测度表示：

$$
p^-(x_k) \approx \frac{1}{N} \sum_{i=1}^N \delta\left(x_k - x_k^{-,(i)}\right)
$$

**代入更新方程**（连续密度函数点乘 Dirac 测度，直接作用于脉冲幅度）：

$$
p(x_k \mid y_{1:k}) \approx p(y_k \mid x_k) \cdot \left( \frac{1}{N} \sum_{i=1}^N \delta_{x_k^{(i)}}(x_k) \right) = \sum_{i=1}^N \left( \frac{p(y_k \mid x_k^{(i)})}{N} \right) \delta_{x_k^{(i)}}(x_k)
$$

归一化幅度，即直接得到权重 $w_k^{(i)} \propto p(y_k \mid x_k^{(i)})$。

### 3. 重采样：经验测度的再等权化

重采样步骤的数学本质，是用一个**无权经验测度**最优逼近**加权经验测度**：

$$
\sum_{i=1}^N w_k^{(i)} \delta_{x_k^{(i)}} \xrightarrow{\text{Weak Convergence}} \frac{1}{N} \sum_{i=1}^N \delta_{x_k^{(i)*}}
$$

---

# 启动迭代例子

#### 1. 状态预测与重新离散化

已知 $p(x_0) \approx \frac{1}{N} \sum_{i=1}^N \delta_{x_0^{(i)}}$。
从每个旧粒子按转移核抽样新粒子 $x_1^{(i)} \sim p(x_1 \mid x_0^{(i)})$（通过采样过程噪声 $n_{x,1}^{(i)}$ 实现），将预测分布**重新写回经验测度**：

$$
p(x_1) \approx \frac{1}{N} \sum_{i=1}^N \delta_{x_1^{(i)}}(x_1)
$$

#### 2. 代入 Bayes 更新（分母积分瞬间消去）

将离散化后的 $p(x_1)$ 代入分母：

$$
\int p(y_1 \mid x_1) p(x_1) dx_1 \approx \int p(y_1 \mid x_1) \left( \frac{1}{N} \sum_{i=1}^N \delta_{x_1^{(i)}}(x_1) \right) dx_1 = \frac{1}{N} \sum_{i=1}^N p(y_1 \mid x_1^{(i)})
$$

#### 3. 得到加权后验经验分布

分子分母代回 Bayes 公式，得：

$$
p(x_1 \mid y_1) = \frac{p(y_1 \mid x_1) \cdot \frac{1}{N} \sum_{i=1}^N \delta_{x_1^{(i)}}(x_1)}{\frac{1}{N} \sum_{j=1}^N p(y_1 \mid x_1^{(j)})} = \sum_{i=1}^N w_1^{(i)} \delta_{x_1^{(i)}}(x_1)
$$

其中权重定义为：

$$
w_1^{(i)} = \frac{p(y_1 \mid x_1^{(i)})}{\sum_{j=1}^N p(y_1 \mid x_1^{(j)})}
$$
