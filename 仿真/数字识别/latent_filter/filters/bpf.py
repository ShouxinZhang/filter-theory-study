"""无输运方法：似然加权后多项重采样。状态静止，重采样只复制粒子而不产生新位置。"""
import torch

from ..observe import log_likelihood


def _count_distinct(anc):
    """每张图像中互不相同的祖先粒子个数。"""
    s = anc.sort(1).values
    return 1 + (s[:, 1:] != s[:, :-1]).sum(1)


@torch.no_grad()
def run(ctx, z0, y_full, jitter=0.0):
    b, n, _ = z0.shape
    z = z0
    anc = torch.arange(n, device=z.device).expand(b, n)       # 祖先下标，用于统计多样性
    for k in range(len(ctx.masks)):
        logw = log_likelihood(ctx.model.restore(z), y_full, ctx.masks[k], ctx.cfg.sigma)
        idx = torch.multinomial(torch.softmax(logw, 1), n, replacement=True)
        z = z.gather(1, idx[..., None].expand_as(z))
        anc = anc.gather(1, idx)
        if jitter > 0:                                        # 人工扰动，用以缓解贫化
            z = z + jitter * torch.randn_like(z)
        yield z, {"distinct": _count_distinct(anc).float()}
