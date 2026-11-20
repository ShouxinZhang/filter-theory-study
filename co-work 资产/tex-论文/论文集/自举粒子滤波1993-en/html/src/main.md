---
title: Novel Approach to Nonlinear/Non-Gaussian Bayesian State Estimation
macros: macros.tex
bib: refs.bib
bib_order: file
lang: en
---

<header class="title">
<h1>Novel Approach to Nonlinear/Non-Gaussian Bayesian State Estimation[^1]</h1>
<p class="subtitle">N. J. Gordon · D. J. Salmond · A. F. M. Smith[^2] · IEE Proceedings-F, Vol. 140, No. 2, pp. 107–113, April 1993</p>
</header>

<p class="h2">Abstract</p>

*An algorithm is introduced for implementing recursive Bayesian state estimation, termed the bootstrap filter. The posterior probability density of the state vector is represented by a cloud of random samples that are propagated through the system dynamics and updated as new observations arrive. Because the method relies neither on linearity nor on Gaussian noise assumptions, it applies directly to general nonlinear state-transition and measurement models. The approach is demonstrated on a bearings-only tracking simulation, together with practical refinements that improve sample efficiency. In this benchmark, the bootstrap filter substantially outperforms the standard extended Kalman filter.*

*Indexing terms: Kalman filter, Sequential estimation, Bayesian filter.*

<!--include 01_introduction_and_bayesian.md-->
<!--include 02_bootstrap_filter.md-->
<!--include 03_simulations.md-->
<!--include 04_conclusions_and_refs.md-->
