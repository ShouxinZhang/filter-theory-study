"""训练：压缩还原算子、类别读出、摊销输运映射。三者均把数据放在显存中按小批量迭代。"""
import time
import torch
from torch import nn

from .nets import CompressRestore, CondNet, mlp


def _batches(n, batch, device):
    """随机打乱后按批给出下标。"""
    perm = torch.randperm(n, device=device)
    for i in range(0, n, batch):
        yield perm[i:i + batch]


def train_compress_restore(cfg, x, log):
    """极小化重构误差 ||x - T_<=(T_=>(x))||^2，联合确定压缩与还原算子。"""
    model = CompressRestore(cfg.n_d).to(x.device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, cfg.ae_epochs)
    for epoch in range(cfg.ae_epochs):
        total = 0.0
        for idx in _batches(len(x), 512, x.device):
            loss = (model.dec(model.enc(x[idx])) - x[idx]).square().mean()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            total += loss.item() * len(idx)
        sched.step()
        if epoch % 5 == 4 or epoch == cfg.ae_epochs - 1:
            log(f"压缩还原 第{epoch + 1}轮 重构均方误差={total / len(x):.5f}")
    model.standardize(x)
    return model.eval().requires_grad_(False)


def train_readout(cfg, z, labels, log):
    """类别读出：由潜坐标预测数字类别；训练时加小扰动，使读出在样本点附近平滑。"""
    net = mlp([cfg.n_d, 256, 256, 10]).to(z.device)
    opt = torch.optim.Adam(net.parameters(), lr=2e-3)
    for epoch in range(cfg.readout_epochs):
        for idx in _batches(len(z), 512, z.device):
            logits = net(z[idx] + 0.1 * torch.randn_like(z[idx]))
            loss = nn.functional.cross_entropy(logits, labels[idx])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
    log(f"类别读出 训练集准确率={(net(z).argmax(-1) == labels).float().mean().item():.4f}")
    return net.eval().requires_grad_(False)


def minimax_losses(f, t_out, z, zbar, feat_f):
    """极大极小目标 J(f,T) 的两个损失。

    J = E[ f(Z,Y) - f(T(Zbar,Y),Y) + 1/2 ||T(Zbar,Y) - Zbar||^2 ]
    返回 (映射 T 要极小化的量, 检验函数 f 要极小化的量即 -J 中与 f 有关的部分)。
    """
    cost = 0.5 * (t_out - zbar).square().sum(-1)
    loss_t = (cost - f(t_out, feat_f).squeeze(-1)).mean()
    loss_f = (f(t_out.detach(), feat_f) - f(z, feat_f)).mean()
    return loss_t, loss_f


def train_amortized(cfg, x, z, cum_masks, log, seconds=None):
    """摊销输运映射：以累积观测及其掩码为条件，离线训练一次，供所有时刻与所有图像使用。

    成对样本 (Z,Y) 直接取自数据：Z 为图像的压缩坐标，Y 为同一图像被掩码后的带噪像素；
    Zbar 为与 Y 无关的先验样本（另一张图像的压缩坐标）。训练不需要似然函数。
    """
    seconds = cfg.amort_seconds if seconds is None else seconds
    dev = x.device
    t_net = CondNet(cfg.n_d, cfg.n_d).to(dev)
    f_net = CondNet(cfg.n_d, 1).to(dev)
    opt_t = torch.optim.Adam(t_net.parameters(), lr=2e-4, betas=(0.5, 0.9))
    opt_f = torch.optim.Adam(f_net.parameters(), lr=2e-4, betas=(0.5, 0.9))
    start, it = time.time(), 0
    while time.time() - start < seconds:
        idx = torch.randint(len(x), (cfg.batch,), device=dev)
        zbar = z[torch.randint(len(x), (cfg.batch,), device=dev)]
        mask = cum_masks[torch.randint(len(cum_masks), (cfg.batch,), device=dev)]
        y = x[idx] + cfg.sigma * torch.randn_like(x[idx])
        # 内层：固定 f，更新映射 T
        for _ in range(cfg.amort_inner):
            t_out = t_net(zbar, t_net.features(y, mask))
            loss_t, _ = minimax_losses(f_net, t_out, z[idx], zbar, f_net.features(y, mask).detach())
            opt_t.zero_grad(set_to_none=True)
            loss_t.backward()
            opt_t.step()
        # 外层：固定 T，更新检验函数 f
        with torch.no_grad():
            t_out = t_net(zbar, t_net.features(y, mask))
        _, loss_f = minimax_losses(f_net, t_out, z[idx], zbar, f_net.features(y, mask))
        opt_f.zero_grad(set_to_none=True)
        loss_f.backward()
        opt_f.step()
        it += 1
        if it % 500 == 0:
            log(f"摊销映射 迭代{it} 用时{time.time() - start:.0f}s loss_T={loss_t.item():.3f} loss_f={loss_f.item():.3f}")
    log(f"摊销映射 训练结束 共{it}次外层迭代")
    return t_net.eval().requires_grad_(False)
