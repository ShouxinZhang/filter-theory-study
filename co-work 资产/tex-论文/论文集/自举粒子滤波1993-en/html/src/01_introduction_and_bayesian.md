<p class="h2">Editorial & Numerical Reconstruction Note</p>

This document is an editable single-column academic reconstruction of Gordon, Salmond, and Smith (1993), *IEE Proceedings-F*, Vol. 140, No. 2, pp. 107–113, rather than publisher source files. All twelve numbered equations (Eqs. ({@eq:1|n})–({@eq:12|n})), eleven figures (Figs. {@fig:1|n}–{@fig:11|n}), and seventeen bibliographic entries ([@r01]–[@r17]) have been verified against the archival edition. Vector and matrix quantities are typeset consistently in bold italic ($\bm{x}_k, \bm{y}_k, \bm{w}_k, \bm{v}_k, \bm{\Phi}, \bm{\Gamma}, \bm{M}_1, \bm{Q}, \bm{I}_2$) with upright transpose $^{\mathrm{T}}$, while scalar variables in the one-dimensional benchmark ($x_k, y_k, w_k, v_k$) and scalar bearing observations ($z_k, v_k$) remain light italic. In the bibliography, the author name in [@r08] is standardized to G. Kitagawa (printed as G. Kittagawa in the original issue).

All eleven figures in {@sec:sim} are regenerated from deterministic numerical simulations of the exact models. In the one-dimensional nonlinear benchmark ({@sec:sim-1d}, $N = 500$ particles, 50 steps), the bootstrap filter achieves an RMSE of $3.6598$ (MAE $2.5408$) and $90\%$ empirical coverage ($45/50$ steps) for its 95% probability region, compared with an EKF RMSE of $20.6309$ (MAE $13.8534$) and $30\%$ coverage ($15/50$ steps); at $k = 21$ ($x_{21} = 19.3983$, $y_{21} = 19.3525$), the bootstrap kernel density captures both symmetric modes with $91.4\%$ posterior mass near $x \approx 19.6$ and $8.6\%$ near $x \approx -19.4$, whereas the EKF collapses to a Gaussian centered at $-32.9165$. In the four-dimensional bearings-only tracking benchmark ({@sec:sim-bearings}, $N = 4000$ particles, 24 steps, roughening factor $K = 0.2$, prior-editing gate $6\sqrt{r}$, and wrapped bearing innovation via $\operatorname{atan2}(y_k, x_k)$ in $(-\pi, \pi]$), the bootstrap filter achieves a position RMSE of $0.18575$, velocity RMSE of $0.00319$, final position error of $0.00334$, and $100\%$ ($24/24$) empirical coverage for both $x$ and $\dot{x}$, whereas the EKF diverges to a position RMSE of $0.41381$ and final error of $0.94009$ ($0/24$ coverage in $x$, $9/24$ in $\dot{x}$). Across the 24 steps, prior editing records $111\,409$ total rejections, peaking at $44\,525$ at $k = 13$ during the observer fly-past ($109\,899$ rejections across $k = 11$ to $15$) and falling to a mean of $21.14$ rejections per step for $k = 18$ to $24$.

# Introduction {#sec:intro}

The Bayesian framework offers a rigorous and general foundation for dynamic state estimation. Its central objective is to construct the probability density function (PDF) of the state vector conditioned on all measurements accumulated up to the current time. When both the system dynamics and observation model are linear and driven by Gaussian noise, the conditional density remains Gaussian at every step, and the Kalman filter recursively propagates its mean and covariance. For nonlinear or non-Gaussian systems, however, closed-form analytical expressions for the required PDF are almost never available.

In practice, recursive nonlinear state estimation is most commonly attempted with the extended Kalman filter (EKF) [@r01], which linearizes the state and measurement equations locally around the predicted state so that the standard Kalman update can be applied. Because this procedure forces a Gaussian approximation onto the posterior PDF, it can severely misrepresent multimodal or skewed distributions and trigger filter divergence. Alternative analytical approximations include the Gaussian sum filter [@r02] and moment-matching schemes that track only the first two moments of the conditional density [@r03,r04]. More direct numerical strategies evaluate the evolving PDF on a discrete grid over the state space [@r05,r06,r07,r08,r09]. Designing an effective grid is difficult in general, and in multi-dimensional state spaces the number of grid nodes—each requiring substantial computation—grows rapidly to prohibitive levels.

This paper introduces an alternative strategy for representing and recursively updating an approximation to the state PDF. Rather than representing the density as an explicit function over the state space, we represent it by a collection of random samples [@r10,r11,r12]. As the sample size increases, this empirical representation converges to an exact, equivalent characterization of the underlying PDF. Moment summaries such as the posterior mean and covariance, as well as quantile estimates, follow immediately from the sample set. When a smooth functional estimate of the PDF is desired—for instance to identify modes or highest posterior density (HPD) intervals—it can be constructed directly from the samples by kernel density estimation [@r13]. An adaptive importance sampling method has been proposed in [@r11], although it leads to large mixture representations and entails high computational cost.

In {@sec:bootstrap} we formulate and justify a recursive sampling algorithm, called the bootstrap filter, for propagating and updating these state samples in the discrete-time setting of {@sec:bayes}. The name reflects the fact that the crucial Bayesian update step is carried out via a weighted bootstrap, inspired by a sampling-resampling result of Smith and Gelfand [@r14]; a related Monte Carlo scheme is described by Muller [@r12]. Sample-based methods eliminate the need to construct a state-space grid because samples naturally concentrate in regions of high posterior probability. Equally important, they accommodate arbitrary functional nonlinearities and arbitrary non-Gaussian process or measurement noise distributions.

Two simulation studies are presented in {@sec:sim}, the second being a four-dimensional bearings-only tracking problem, where the performance of the bootstrap filter is compared directly against that of the standard EKF.

# Recursive Bayesian State Estimation {#sec:bayes}

We consider a discrete-time dynamic system whose state vector $\bm{x}_k \in \mathbb{R}^n$ evolves according to the state-transition model
$$ {#eq:1}
\bm{x}_{k+1} = \bm{f}_k(\bm{x}_k, \bm{w}_k)
$$
where $\bm{f}_k : \mathbb{R}^n \times \mathbb{R}^m \to \mathbb{R}^n$ is the system transition function and $\bm{w}_k \in \mathbb{R}^m$ is a zero-mean white noise sequence independent of past and current states, with a known PDF. At discrete time instants, observations $\bm{y}_k \in \mathbb{R}^p$ become available through the measurement equation
$$ {#eq:2}
\bm{y}_k = \bm{h}_k(\bm{x}_k, \bm{v}_k)
$$
where $\bm{h}_k : \mathbb{R}^n \times \mathbb{R}^r \to \mathbb{R}^p$ is the measurement function and $\bm{v}_k \in \mathbb{R}^r$ is another zero-mean white noise sequence with known PDF, independent of past and current states as well as the process noise. We assume that the initial state PDF $p(\bm{x}_1 \mid D_0) \equiv p(\bm{x}_1)$ and the functional forms $\bm{f}_i$ and $\bm{h}_i$ for $i = 1, \dots, k$ are known. The information available at step $k$ consists of the measurement history $D_k = \{\bm{y}_i : i = 1, \dots, k\}$.

The estimation goal is to determine the conditional PDF of the current state given all available data, $p(\bm{x}_k \mid D_k)$. In principle, this density can be computed recursively in two stages: prediction and update. Suppose that the posterior PDF at time $k - 1$, $p(\bm{x}_{k-1} \mid D_{k-1})$, is known. Using the system dynamics, the one-step-ahead prior PDF at time $k$ is given by the Chapman–Kolmogorov integral:
$$ {#eq:3}
p(\bm{x}_k \mid D_{k-1}) = \int p(\bm{x}_k \mid \bm{x}_{k-1}) p(\bm{x}_{k-1} \mid D_{k-1}) \, \mathrm{d}\bm{x}_{k-1}.
$$
Here the probabilistic transition model $p(\bm{x}_k \mid \bm{x}_{k-1})$ defines a Markov process determined by the state equation and the known distribution of $\bm{w}_{k-1}$:
$$
p(\bm{x}_k \mid \bm{x}_{k-1}) = \int p(\bm{x}_k \mid \bm{x}_{k-1}, \bm{w}_{k-1}) p(\bm{w}_{k-1} \mid \bm{x}_{k-1}) \, \mathrm{d}\bm{w}_{k-1}.
$$
Since $p(\bm{w}_{k-1} \mid \bm{x}_{k-1}) = p(\bm{w}_{k-1})$ by independence, this reduces to
$$ {#eq:4}
p(\bm{x}_k \mid \bm{x}_{k-1}) = \int \delta\bigl(\bm{x}_k - \bm{f}_{k-1}(\bm{x}_{k-1}, \bm{w}_{k-1})\bigr) p(\bm{w}_{k-1}) \, \mathrm{d}\bm{w}_{k-1}
$$
where $\delta(\cdot)$ denotes the Dirac delta function. The delta function arises because, once $\bm{x}_{k-1}$ and $\bm{w}_{k-1}$ are fixed, $\bm{x}_k$ is determined purely deterministically through {@eq:1}. When the new measurement $\bm{y}_k$ arrives at step $k$, Bayes' rule updates the predicted prior to yield the posterior PDF:
$$ {#eq:5}
p(\bm{x}_k \mid D_k) = \frac{p(\bm{y}_k \mid \bm{x}_k) p(\bm{x}_k \mid D_{k-1})}{p(\bm{y}_k \mid D_{k-1})}
$$
where the normalizing denominator is
$$ {#eq:6}
p(\bm{y}_k \mid D_{k-1}) = \int p(\bm{y}_k \mid \bm{x}_k) p(\bm{x}_k \mid D_{k-1}) \, \mathrm{d}\bm{x}_k.
$$
The likelihood $p(\bm{y}_k \mid \bm{x}_k)$ is specified by the measurement equation and the known distribution of $\bm{v}_k$:
$$ {#eq:7}
p(\bm{y}_k \mid \bm{x}_k) = \int \delta\bigl(\bm{y}_k - \bm{h}_k(\bm{x}_k, \bm{v}_k)\bigr) p(\bm{v}_k) \, \mathrm{d}\bm{v}_k.
$$

In the update step {@eq:5}, the observation $\bm{y}_k$ modifies the predicted prior from the previous time step to produce the desired posterior state density.

Together, the recursive relations in {@eq:3} and {@eq:5} constitute the formal solution to the recursive Bayesian estimation problem. Closed-form analytical solutions exist only for a narrow class of models, most notably the Kalman filter, which requires $\bm{f}_k$ and $\bm{h}_k$ to be linear and $\bm{w}_k$ and $\bm{v}_k$ to be additive Gaussian noises with known covariances (see, for example, [@r15,r16]). In many realistic applications these restrictive assumptions do not hold, motivating practical implementation methods that allow models to be formulated from physical realism rather than analytical convenience.
