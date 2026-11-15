# 数字识别的潜空间输运滤波

论文《联合优化下的非线性滤波：神经网络与输运方法》机器学习一章的实验代码。
在 MNIST 上，把逐块观测下的数字识别作为状态静止的滤波问题，在压缩算子给出的潜空间中比较五种粒子更新：
自举粒子滤波（BPF），加扰动的 BPF，集合输运粒子滤波（ETPF），逐步训练的输运映射（OTPF），摊销输运映射（摊销 OTPF）。

## 目录

```text
run.py                  入口：阶段甲（主实验）与阶段乙（多种子与消融）
tune_baselines.py       对照方法的超参数选取记录
official_otpf.py        调用作者官方代码的适配脚本（未跑完，结果未使用）
latent_filter/
├── config.py           全部超参数
├── data.py             数据读取
├── observe.py          窗口观测模型与似然
├── nets.py             压缩还原算子，条件网络，成批小网络
├── train.py            三个网络的训练与极大极小损失
├── evaluate.py         统一的评估流程与指标
├── plots.py            绘图
└── filters/            bpf，etpf，otpf_online，amortized
outputs/
├── metrics/            main.json（主实验），extra.json（多种子与消融）
└── figures/            曲线，耗时，粒子示例
```

`data/`，`outputs/checkpoints/`，`outputs/logs/` 与 `third_party/` 不纳入版本管理。

## 复现

环境：Python 3.12，PyTorch，torchvision，matplotlib，一块显卡。MNIST 缺失时自动下载到 `data/`。

```bash
python run.py --fresh
```

主实验约 7 分钟，全部约 19 分钟（笔记本 RTX 5090）。`--stage a` 只跑主实验，`--smoke` 为一分钟内的冒烟测试，
`--set 键=值` 可覆盖 `latent_filter/config.py` 中的任一超参数。训练好的网络存入 `outputs/checkpoints/`，再次运行时自动复用。

## 主要结果

256 个粒子，500 幅测试图像，3 个随机种子；全图观测后的识别准确率与每幅图像每步的在线耗时。

| 方法 | 识别准确率 | 在线耗时 |
| --- | --- | --- |
| BPF | 49.2% | 0.034 ms |
| BPF 加扰动 | 53.9% | 0.034 ms |
| ETPF | 54.7% | 0.24 ms |
| OTPF | 81.8% | 17.2 ms |
| 摊销 OTPF | 96.8% | 0.015 ms |

完整图像直接压缩后读出的准确率为 97.8%，是各方法的上限参照。

## 关于对照方法的说明

- 五种方法均由本文在同一框架下独立实现，共用同一压缩还原算子，同一批初始粒子与同一批观测噪声。
- ETPF 与 OTPF 的超参数由 `tune_baselines.py` 在前 100 幅测试图像上选取，这对它们有利；摊销 OTPF 不参与该选参。
- OTPF 按原文（Al-Jarrah 等）的思路重新实现，并加入观测降维以稳定训练，不是作者的官方代码。
  曾尝试直接调用官方实现（`official_otpf.py`），因其固定在 CPU 上逐幅运行，耗时过长而中止，没有结果。
  因此本实验不能对官方实现的表现下任何结论。
- 摊销映射离线使用全部训练样本；依赖权重的方法对每幅图像只有 N 个先验粒子。
- 网络只训练一次；随机种子只影响初始粒子与观测噪声；消融为单个种子。

## 第三方代码

`official_otpf.py` 需要作者的官方仓库，本仓库不附带：

```bash
git clone --depth 1 https://github.com/Mohd9485/Filtering-with-Optimal-Transport.git third_party/Filtering-with-Optimal-Transport
```
