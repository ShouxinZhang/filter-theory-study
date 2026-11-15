"""摊销输运映射（本文改进）：离线训练一次，在线每步只做一次前向计算。

状态静止时，第 k 步的滤波后验等于以累积观测对初始先验作一次更新，
故每步都从初始粒子 z0 出发，不存在逐步误差累积。
"""
import torch


@torch.no_grad()
def run(ctx, z0, y_full):
    b, n, _ = z0.shape
    for k in range(len(ctx.masks)):
        feat = ctx.t_net.features(y_full, ctx.cum_masks[k].expand_as(y_full))
        yield ctx.t_net(z0, feat[:, None].expand(b, n, -1)), {}
