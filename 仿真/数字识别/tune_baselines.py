"""对照方法的超参数选取记录。

在前 100 幅测试图像上比较 ETPF 与逐步训练的 OTPF 的若干超参数，取其中表现最好的一组写入 config.py。
在测试图像上为对照方法选参，对对照方法有利；本文方法（摊销输运映射）不参与此处选参。
须先运行 run.py 生成检查点。

用法：python tune_baselines.py etpf | etpf2 | otpf
"""
import sys
from dataclasses import replace
import torch
from latent_filter import data
from latent_filter.config import OUT, Config
from latent_filter.evaluate import evaluate, make_inputs
from latent_filter.filters import bpf, etpf, otpf_online
from run import prepare

cfg = replace(Config(), n_test=100)
ds = data.load(torch.device("cuda"))
ctx, z_tr, _ = prepare(cfg, ds, OUT, print, False)             # 读取主实验的检查点
x, lab = ds[2][:cfg.n_test], ds[3][:cfg.n_test]
z0, y = make_inputs(cfg, z_tr, x, 0)


def show(name, fn, **over):
    ctx.cfg = replace(cfg, **over)
    r = evaluate(ctx, fn, z0, y, x, lab)
    acc = " ".join(f"{a:.2f}" for a in r["acc"][3::4])
    print(f"{name:28s} acc@4,8,12,16= {acc} | spread@8,16={r['spread'][7]:.3f},{r['spread'][15]:.3f} | brier16={r['brier'][-1]:.3f} | {sum(r['time'])/16*1e3:.2f}ms", flush=True)


which = sys.argv[1]
if which == "etpf":
    show("bpf", bpf.run)
    for e in (0.005, 0.02, 0.05, 0.2):
        for it in (50, 300):
            show(f"etpf eps={e} it={it}", etpf.run, eps_rel=e, sinkhorn_iters=it)
if which == "otpf":
    for kw in (dict(online_lr=5e-4, online_iters=100, online_inner=5),
               dict(online_ypca=8, online_iters=150),
               dict(online_ypca=8, online_lr=5e-4, online_iters=300, online_inner=5),
               dict(online_ypca=4, online_lr=5e-4, online_iters=300, online_inner=5)):
        show("otpf " + " ".join(f"{k[7:]}={v}" for k, v in kw.items()), otpf_online.run, **kw)
if which == "etpf2":
    for e in (0.002, 0.005, 0.01):
        show(f"etpf eps={e}", etpf.run, eps_rel=e)
