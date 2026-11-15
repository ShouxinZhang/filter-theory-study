"""评估：在同一批初始粒子与同一批观测噪声上运行各方法，逐步统计指标。"""
import time
import torch


class Context:
    """各滤波器共用的只读环境。"""

    def __init__(self, cfg, model, readout, masks, cum_masks, t_net=None):
        self.cfg, self.model, self.readout = cfg, model, readout
        self.masks, self.cum_masks, self.t_net = masks, cum_masks, t_net


def make_inputs(cfg, z_train, x_test, seed):
    """固定随机种子，生成初始粒子（先验样本）与带噪完整图像，供所有方法共用。"""
    g = torch.Generator(device=x_test.device).manual_seed(seed)
    idx = torch.randint(len(z_train), (len(x_test), cfg.n_particles), generator=g, device=x_test.device)
    noise = torch.randn(x_test.shape, generator=g, device=x_test.device)
    return z_train[idx], x_test + cfg.sigma * noise


@torch.no_grad()
def step_metrics(ctx, z, x, labels):
    """单步指标，按图像给出，形状均为 [B]。"""
    votes = torch.nn.functional.one_hot(ctx.readout(z).argmax(-1), 10).float().mean(1)   # 类别后验的粒子近似
    onehot = torch.nn.functional.one_hot(labels, 10).float()
    return {
        "acc": (votes.argmax(-1) == labels).float(),                     # 众数判决是否正确
        "brier": (votes - onehot).square().sum(-1),                      # 类别后验的平方误差
        "p_true": (votes * onehot).sum(-1),                              # 真实类别所占粒子比例
        "mse": (ctx.model.restore(z).mean(1) - x).square().mean(-1),     # 还原均值的像素均方误差
        "spread": z.var(1).mean(-1).sqrt(),                              # 粒子在潜空间中的离散程度
    }


def evaluate(ctx, run_fn, z0, y_full, x, labels):
    """分块运行某一方法，返回 {指标名: 长度为 K 的列表}；time 为每张图像每步的平均在线耗时（秒）。"""
    k_steps = len(ctx.masks)
    chunk = max(1, 32000 // z0.shape[1])                        # 按粒子数调整分块，控制显存
    sums, seconds = {}, [0.0] * k_steps
    for s in range(0, len(x), chunk):
        sl = slice(s, s + chunk)
        gen = run_fn(ctx, z0[sl], y_full[sl])
        for k in range(k_steps):
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            z, extra = next(gen)
            torch.cuda.synchronize()
            seconds[k] += time.perf_counter() - t0
            m = step_metrics(ctx, z, x[sl], labels[sl])
            m.update(extra)
            for name, v in m.items():
                sums.setdefault(name, torch.zeros(k_steps, device=x.device))[k] += v.sum()
    out = {name: (v / len(x)).tolist() for name, v in sums.items()}
    out["time"] = [t / len(x) for t in seconds]
    return out
