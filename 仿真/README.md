# 仿真

论文《联合优化下的非线性滤波——神经网络与输运方法》第 4 章的全部实验代码与数据。

| 目录 | 内容 | 对应论文 |
| --- | --- | --- |
| [Gordon基准](Gordon基准/README.md) | EKF，BPF，EnKF，熵正则 ETPF 的 C++ 实现与运行脚本 | 4.1 至 4.3 节 |
| [Logistic零过程噪声](Logistic零过程噪声/README.md) | 零过程噪声下的粒子贫化与四项误差分解 | 4.4 节 |
| [数字识别](数字识别/README.md) | 潜空间中的五种粒子更新，含摊销输运映射 | 4.5 节 |
| [论文图表](论文图表/README.md) | 第 4 章全部图表的生成脚本与所用数据 | 第 4 章图表 |
| [code](code/README.md) | 通用 C++ 滤波库（BPF 与精确输运的 ETPF），供 Logistic 实验调用 | 4.4 节 |
| [docs](docs/README.md) | 上述 C++ 库的数学规范 | |

各目录的 README 给出依赖与复现命令。在作者的机器上，Gordon 基准约 30 秒，Logistic 实验约 25 秒，数字识别约 19 分钟。
