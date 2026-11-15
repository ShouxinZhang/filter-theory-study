"""逐步训练的输运映射（原文做法）：每个时刻用当前粒子及其模拟观测重新求解极大极小问题。"""
import torch

from ..nets import BatchedMLP
from ..train import minimax_losses


class _Cat(torch.nn.Module):
    """把成批小网络包装成 net(z, y) 的调用形式；residual=True 时输出 z + g(z,y)。"""

    def __init__(self, net, residual):
        super().__init__()
        self.net, self.residual = net, residual

    def forward(self, z, y):
        out = self.net(torch.cat([z, y], -1))
        return z + out if self.residual else out


@torch.enable_grad()                                           # 即使调用方关闭了梯度，这里也要训练
def run(ctx, z0, y_full):
    cfg = ctx.cfg
    b, n, d = z0.shape
    r2, h = cfg.window ** 2, cfg.online_hidden
    q = cfg.online_ypca or r2                                  # 送入网络的观测维数
    # 每张图像一对网络；跨时刻沿用参数作热启动
    t_net = _Cat(BatchedMLP(b, [d + q, h, h, d]), True).to(z0.device)
    f_net = _Cat(BatchedMLP(b, [d + q, h, h, 1]), False).to(z0.device)
    opt_t = torch.optim.Adam(t_net.parameters(), lr=cfg.online_lr, betas=(0.5, 0.9))
    opt_f = torch.optim.Adam(f_net.parameters(), lr=cfg.online_lr, betas=(0.5, 0.9))
    z = z0
    for k in range(len(ctx.masks)):
        pix = ctx.masks[k].bool()
        with torch.no_grad():                                  # 为每个粒子模拟一个观测，得到成对样本 (Z,Y)
            y_sim = ctx.model.restore(z)[..., pix]
            y_sim = y_sim + cfg.sigma * torch.randn_like(y_sim)
            y_obs = y_full[:, None, pix]
            if cfg.online_ypca:                                # 观测降维：按模拟观测的主方向投影并标准化
                mean = y_sim.mean(1, keepdim=True)
                _, sv, vh = torch.linalg.svd(y_sim - mean, full_matrices=False)
                proj = vh[:, :q].transpose(1, 2) / (sv[:, None, :q] / n ** 0.5 + 1e-3)
                y_sim, y_obs = (y_sim - mean) @ proj, (y_obs - mean) @ proj
        for _ in range(cfg.online_iters):
            zbar = z[:, torch.randperm(n, device=z.device)]   # 与 Y 无关的预测粒子副本
            for _ in range(cfg.online_inner):
                loss_t, _ = minimax_losses(f_net, t_net(zbar, y_sim), z, zbar, y_sim)
                opt_t.zero_grad(set_to_none=True)
                (loss_t * b).backward()                        # 乘 b：各网络的梯度互不平均
                opt_t.step()
            with torch.no_grad():
                t_out = t_net(zbar, y_sim)
            _, loss_f = minimax_losses(f_net, t_out, z, zbar, y_sim)
            opt_f.zero_grad(set_to_none=True)
            (loss_f * b).backward()
            opt_f.step()
        with torch.no_grad():                                  # 代入真实观测，更新粒子
            z = t_net(z, y_obs.expand(b, n, q))
        yield z, {}
