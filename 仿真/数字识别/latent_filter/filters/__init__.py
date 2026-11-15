"""四种粒子更新。统一接口：run(ctx, z0, y_full) 为生成器，每步给出 (粒子 [B,N,n_d], 附加信息字典)。

ctx 须含：model（压缩还原）、masks / cum_masks（单步与累积掩码）、cfg；摊销方法另需 ctx.t_net。
"""
from . import amortized, bpf, etpf, otpf_online  # noqa: F401
