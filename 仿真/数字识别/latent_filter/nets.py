"""网络定义：压缩还原算子、类别读出、摊销映射与检验函数、成批的小网络。"""
import math
import torch
from torch import nn


def mlp(sizes, last_act=None):
    """按 sizes 构造全连接网络，隐藏层用 SiLU。"""
    layers = []
    for i in range(len(sizes) - 1):
        layers.append(nn.Linear(sizes[i], sizes[i + 1]))
        if i < len(sizes) - 2:
            layers.append(nn.SiLU())
    if last_act is not None:
        layers.append(last_act)
    return nn.Sequential(*layers)


class CompressRestore(nn.Module):
    """压缩算子 T_=> 与还原算子 T_<=。潜坐标经标准化，使各维均值为 0、方差为 1。"""

    def __init__(self, n_d):
        super().__init__()
        self.enc = mlp([784, 512, 256, n_d])
        self.dec = mlp([n_d, 256, 512, 784], nn.Sigmoid())
        self.register_buffer("mu", torch.zeros(n_d))
        self.register_buffer("std", torch.ones(n_d))

    def compress(self, x):
        return (self.enc(x) - self.mu) / self.std

    def restore(self, z):
        return self.dec(z * self.std + self.mu)

    @torch.no_grad()
    def standardize(self, x):
        """训练结束后调用一次：用训练集潜坐标的均值与标准差固定标准化常数。"""
        z = self.enc(x)
        self.mu.copy_(z.mean(0))
        self.std.copy_(z.std(0))


class CondNet(nn.Module):
    """以（潜变量, 累积观测, 掩码）为输入的网络；out=n_d 时作映射 T，out=1 时作检验函数 f。"""

    def __init__(self, n_d, out, width=512, feat=128):
        super().__init__()
        self.obs = mlp([2 * 784, width, feat])          # 观测特征提取
        self.body = mlp([n_d + feat, width, width, out])

    def features(self, y, mask):
        return self.obs(torch.cat([y * mask, mask], -1))

    def forward(self, z, feat):
        return self.body(torch.cat([z, feat], -1))


class BatchedMLP(nn.Module):
    """B 个互相独立的小网络并行计算：输入 [B, N, in]，输出 [B, N, out]。

    逐步训练方法须为每张测试图像各训练一对网络，这里用成批矩阵乘法一次算完。
    """

    def __init__(self, n_nets, sizes):
        super().__init__()
        self.w = nn.ParameterList()
        self.b = nn.ParameterList()
        for i in range(len(sizes) - 1):
            bound = 1 / math.sqrt(sizes[i])
            self.w.append(nn.Parameter(torch.empty(n_nets, sizes[i], sizes[i + 1]).uniform_(-bound, bound)))
            self.b.append(nn.Parameter(torch.zeros(n_nets, 1, sizes[i + 1])))

    def forward(self, x):
        for i, (w, b) in enumerate(zip(self.w, self.b)):
            x = torch.baddbmm(b, x, w)
            if i < len(self.w) - 1:
                x = torch.nn.functional.silu(x)
        return x
