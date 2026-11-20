---
title: 非线性与非正态条件状态估计的一种新方法
macros: macros.tex
bib: refs.bib
bib_order: file
---

<header class="title">
<h1>非线性与非正态条件状态估计的一种新方法[^1]</h1>
<p class="subtitle">N. J. Gordon · D. J. Salmond · A. F. M. Smith[^2] · IEE Proceedings-F, Vol. 140, No. 2, pp. 107–113, April 1993</p>
</header>

<p class="h2">摘要</p>

*本文提出一种用于实现递推条件概率滤波的新算法，即条件自举粒子滤波器（bootstrap filter）。所需的状态向量概率密度函数由一组随机样本（粒子）表示，并经由该算法完成递推更新与向前传播。该方法不受线性模型或正态噪声假设的约束，适用于任意形式的状态转移模型与观测模型。文中给出了一维强非线性模型以及二维纯方位目标追踪（bearings-only tracking）问题的数值仿真算例，并引入了旨在提升基本算法计算效率的样本抖动加糙与单步超前先验筛选方案。仿真结果表明，在强非线性与非正态情形下，条件自举滤波器的估计性能显著优于标准的一阶线性化正态滤波器。*

<!--include 00_导读与符号约定.md-->
<!--include 01_递推条件状态估计.md-->
<!--include 02_条件自举滤波器.md-->
<!--include 03_数值仿真算例.md-->
<!--include 04_结论与参考文献.md-->
<!--include 05_译校与审核附录.md-->
