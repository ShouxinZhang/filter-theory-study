以Gordon 1993的一维非线性例子仿真作为例子，我需要为我的论文作一个仿真的baseline.

算法例子还包括 [Filtering-with-Optimal-Transport](https://github.com/Mohd9485/Filtering-with-Optimal-Transport) 中的stactic example.

要求:

EKF,BPF,EnKF,OTPF（sinkhorn加速求解）作为baseline算法.

- 符号习惯必须和参考文件保持一致。
- 噪声为正态分布噪声
- 使用C++编写算法（防止python IO缓慢等影响结果），并且，要求算法评估实现模块化分离，也就是，仿真真实数据模块固定（类似于LLM benchmark），而算法模块和评估模块也是分离的，算法输出filter在线滤波数据，而评估模块返回误差等数据。
- 必须写明算法的数学原理以及其简短证明（由于目前LLM推理能力非常强，我们鼓励简洁的纲要性说明而非冗长的细节铺垫）
- 图表方面的要求，和ICLR保持一致，三线表，上下指标，最优指标加粗，都需要有。
- 需要做消融实验（涉及粒子方法的，不同N；不同的时间步长，例如0.05,0.1,0.2,0.5,粗糙的时间步长更考验非线性）
- 明确记录 CPU 型号、内存及操作系统
- 使用全英文写作，最后输出一个仿真baseline tex pdf.