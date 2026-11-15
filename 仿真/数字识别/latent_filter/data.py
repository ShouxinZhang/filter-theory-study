"""数据：把 MNIST 整体读入显存，像素归一化到 [0,1] 并展平为 784 维。"""
import torch
from torchvision import datasets

from .config import DATA


def load(device):
    """返回 (训练图像, 训练标签, 测试图像, 测试标签)，全部位于 device 上。"""
    out = []
    for train in (True, False):
        d = datasets.MNIST(str(DATA), train=train, download=True)
        out.append(d.data.to(device).float().div_(255).flatten(1))
        out.append(d.targets.to(device))
    return out
