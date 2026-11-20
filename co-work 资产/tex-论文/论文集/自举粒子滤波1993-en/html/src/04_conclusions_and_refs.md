# Conclusions {#sec:conc}

A new algorithm—the bootstrap filter—has been introduced for recursive Bayesian state estimation. By representing the evolving posterior distribution as a collection of random samples, the method removes the analytical tractability constraints that limit classical nonlinear filters.

In many realistic problems, however, the number of distinct values in the sample cloud can collapse rapidly over successive updates. To address this sample impoverishment, two somewhat ad hoc remedies—roughening and prior editing—have been developed and demonstrated on a four-dimensional nonlinear bearings-only tracking benchmark. Even with a moderate sample size, the bootstrap filter substantially outperforms the standard extended Kalman filter.

Further research is needed to establish theoretically grounded, practical techniques for preventing sample collapse. Useful guidelines are also needed to determine the sample size required for reliable bootstrap filter performance in a given problem, alongside more extensive Monte Carlo studies to quantify filtering accuracy across important nonlinear estimation benchmarks.

# References {#sec:refs}

<!--REFS-->

[^1]: Paper 9241F (E5), first received 27th April 1992 and in revised form 8th October 1992.
[^2]: N. J. Gordon and D. J. Salmond were with the Defence Research Agency, Farnborough, United Kingdom; A. F. M. Smith was with the Department of Mathematics (Statistics Section), Imperial College, London, United Kingdom. This work was supported by DRA Farnborough.

<!--FOOTNOTES-->
