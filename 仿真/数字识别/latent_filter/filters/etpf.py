"""集合输运粒子滤波：以熵正则最优输运耦合把加权粒子变换为等权粒子，X+ = X- T，T = N Pi。"""
import math
import torch

from ..observe import log_likelihood


def sinkhorn_transform(z, log_a, eps_rel, iters):
    """对数域矩阵缩放。行边缘为权重 a，列边缘为 1/N；返回变换后的粒子。

    z: [B, N, d]；log_a: [B, N] 对数权重。最后一步更新列势，保证列边缘严格等于 1/N，
    因而每个新粒子是旧粒子的凸组合。
    """
    n = z.shape[1]
    cost = torch.cdist(z, z).square()
    eps = (eps_rel * cost.mean((1, 2), keepdim=True)).clamp_min(1e-6)   # 粒子重合时防止除零
    kern = -cost / eps
    log_b = -math.log(n)
    f = torch.zeros_like(log_a)
    g = torch.zeros_like(log_a)
    for _ in range(iters):
        f = log_a - torch.logsumexp(kern + g[:, None, :], 2)
        g = log_b - torch.logsumexp(kern + f[:, :, None], 1)
    plan = torch.exp(kern + f[:, :, None] + g[:, None, :])    # 耦合矩阵 Pi，[B, N, N]
    return n * plan.transpose(1, 2) @ z


@torch.no_grad()
def run(ctx, z0, y_full):
    z = z0
    for k in range(len(ctx.masks)):
        logw = log_likelihood(ctx.model.restore(z), y_full, ctx.masks[k], ctx.cfg.sigma)
        z = sinkhorn_transform(z, torch.log_softmax(logw, 1), ctx.cfg.eps_rel, ctx.cfg.sinkhorn_iters)
        yield z, {}
