$$
\begin{aligned}
&\mathbb{P}_{\bm{w}} = \sum_{i=1}^N w_i \delta_{x_i^-}, \quad \mathbb{P}_N = \frac{1}{N}\sum_{j=1}^N \delta_{x_j^-}, \quad \mathbb{P}_{(X,Y)} = \sum_{i=1}^N \sum_{j=1}^N P_{ij} \delta_{(x_i^-, x_j^-)}, \quad P_{ij} \ge 0 \\
&(\pi_1)_\# \mathbb{P}_{(X,Y)} = \sum_{i=1}^N \left( \sum_{j=1}^N P_{ij} \right) \delta_{x_i^-} = \mathbb{P}_{\bm{w}} \iff \bm{P}\mathbf{1}_N = \bm{w} \\
&(\pi_2)_\# \mathbb{P}_{(X,Y)} = \sum_{j=1}^N \left( \sum_{i=1}^N P_{ij} \right) \delta_{x_j^-} = \mathbb{P}_N \iff \bm{P}^\mathrm{T}\mathbf{1}_N = \frac{1}{N}\mathbf{1}_N \\
&\mathbb{E}_{(X,Y)\sim\mathbb{P}_{(X,Y)}}\left[\|X - Y\|^2\right] = \iint \|x - y\|^2 \, \mathrm{d}\mathbb{P}_{(X,Y)}(x,y) = \sum_{i,j=1}^N P_{ij} \|x_i^- - x_j^-\|^2 = \operatorname{tr}(\bm{C}^\mathrm{T}\bm{P}) \\
&\bm{P}^\star = \arg\min_{\bm{P} \ge 0} \left\{ \operatorname{tr}(\bm{C}^\mathrm{T}\bm{P}) \;\middle|\; \bm{P}\mathbf{1}_N = \bm{w}, \; \bm{P}^\mathrm{T}\mathbf{1}_N = \frac{1}{N}\mathbf{1}_N \right\}
\end{aligned}
$$
