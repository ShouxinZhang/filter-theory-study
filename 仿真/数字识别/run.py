"""入口：阶段甲（主实验，目标 10 分钟内）与阶段乙（补充实验，总计 30 分钟内）。

用法：
    python run.py                # 阶段甲 + 阶段乙
    python run.py --stage a      # 仅主实验
    python run.py --smoke        # 冒烟测试，结果写入 outputs/smoke/
检查点：训练好的网络存入 outputs/checkpoints/，再次运行时自动复用；--fresh 强制重训。
"""
import argparse
import json
import time
from dataclasses import replace
from functools import partial

import torch

from latent_filter import data, plots, train
from latent_filter.config import OUT, Config
from latent_filter.evaluate import Context, evaluate, make_inputs
from latent_filter.filters import amortized, bpf, etpf, otpf_online
from latent_filter.observe import window_masks

START = time.time()
LIMIT_A, LIMIT_ALL = 10 * 60, 30 * 60          # 两级时限（秒）


def elapsed():
    return time.time() - START


def make_logger(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a")

    def log(msg):
        line = f"[{elapsed():7.1f}s] {msg}"
        print(line, flush=True)
        fh.write(line + "\n")
        fh.flush()
    return log


def cached(path, build, fresh):
    """检查点机制：文件存在则读取，否则构建并保存。"""
    if path.exists() and not fresh:
        return torch.load(path, weights_only=False)
    obj = build()
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(obj, path)
    return obj


def prepare(cfg, ds, out, log, fresh, amort_seconds=None):
    """训练（或读取）压缩还原、类别读出、摊销映射，返回评估环境与训练集潜坐标。"""
    x_tr, y_tr, x_te, y_te = ds
    ck = out / "checkpoints"
    tag = f"nd{cfg.n_d}"
    model = cached(ck / f"compress_restore_{tag}.pt", lambda: train.train_compress_restore(cfg, x_tr, log), fresh)
    with torch.no_grad():
        z_tr, z_te = model.compress(x_tr), model.compress(x_te)
        rec = (model.restore(z_te) - x_te).square().mean().item()
    readout = cached(ck / f"readout_{tag}.pt", lambda: train.train_readout(cfg, z_tr, y_tr, log), fresh)
    ceiling = (readout(z_te).argmax(-1) == y_te).float().mean().item()
    log(f"n_d={cfg.n_d} 测试集重构均方误差={rec:.5f} 完整图像直接压缩后读出的准确率={ceiling:.4f}")
    masks, cum = window_masks(cfg.window, x_tr.device)
    t_net = cached(ck / f"amortized_{tag}.pt",
                   lambda: train.train_amortized(cfg, x_tr, z_tr, cum, log, amort_seconds), fresh)
    return Context(cfg, model, readout, masks, cum, t_net), z_tr, {"recon_mse": rec, "ceiling_acc": ceiling}


def runners(cfg, with_online=True):
    """方法名 -> 滤波器。粒子数超过 1024 时不运行集合输运方法（N x N 耦合过大）。"""
    r = {"bpf": bpf.run, "bpf_jitter": partial(bpf.run, jitter=cfg.jitter)}
    if cfg.n_particles <= 1024:
        r["etpf"] = etpf.run
    if with_online:
        r["otpf"] = otpf_online.run
    r["amortized"] = amortized.run
    return r


def run_all(ctx, z_tr, ds, seed, log, with_online=True):
    """在前 n_test 张测试图像上评估全部方法。"""
    cfg = ctx.cfg
    x, labels = ds[2][:cfg.n_test], ds[3][:cfg.n_test]
    z0, y_full = make_inputs(cfg, z_tr, x, seed)
    res = {}
    for name, fn in runners(cfg, with_online).items():
        t0 = time.time()
        res[name] = evaluate(ctx, fn, z0, y_full, x, labels)
        r = res[name]
        log(f"  {name:11s} 末步准确率={r['acc'][-1]:.4f} 中段(k=8)准确率={r['acc'][7] if len(r['acc']) > 7 else float('nan'):.4f} "
            f"末步Brier={r['brier'][-1]:.4f} 每图每步={sum(r['time']) / len(r['time']) * 1e3:.3f}ms 评估用时={time.time() - t0:.1f}s")
    return res


def save(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1))


def stage_a(cfg, ds, out, log, fresh):
    log("=== 阶段甲：主实验 ===")
    ctx, z_tr, info = prepare(cfg, ds, out, log, fresh)
    res = run_all(ctx, z_tr, ds, cfg.seed, log)
    save({"config": cfg.to_dict(), "info": info, "results": res}, out / "metrics" / "main.json")
    plots.curves(res, out / "figures" / "curves.png")
    plots.runtime(res, out / "figures" / "runtime.png")
    # 示例图：取一张测试图像，展示各方法在若干时刻的粒子
    pick = 18                                                   # 测试集第 18 张，数字 3
    x1 = ds[2][pick:pick + 1]
    z0, y1 = make_inputs(cfg, z_tr, x1, cfg.seed)
    show = {k: v for k, v in runners(cfg).items() if k != "bpf_jitter"}
    steps = [s for s in (6, 10, 16) if s <= cfg.n_steps]
    plots.gallery(ctx, show, z0, y1, steps, out / "figures" / "gallery.png")
    log(f"阶段甲结束，累计用时 {elapsed():.0f}s（时限 {LIMIT_A}s）")
    return ctx, z_tr


def stage_b(cfg, ds, out, log, ctx, z_tr, fresh):
    """补充实验。每项开始前检查剩余时间，不足则跳过并记录。"""
    log("=== 阶段乙：补充实验 ===")
    extra = {"seeds": {}, "particles": {}, "latent_dim": {}, "skipped": []}

    def room(need, name):
        ok = elapsed() + need < LIMIT_ALL - 30
        if not ok:
            extra["skipped"].append(name)
            log(f"跳过 {name}：剩余时间不足")
        return ok

    for seed in (1, 2):                                         # 随机种子：重抽初始粒子与观测噪声
        if room(170, f"seed{seed}"):
            log(f"随机种子 {seed}")
            extra["seeds"][seed] = run_all(ctx, z_tr, ds, seed, log)
            save(extra, out / "metrics" / "extra.json")
    for n in (64, 1024, 4096):                                        # 粒子数消融（不含逐步训练方法）
        if room(60, f"N{n}"):
            log(f"粒子数 N={n}")
            c2 = Context(replace(cfg, n_particles=n), ctx.model, ctx.readout, ctx.masks, ctx.cum_masks, ctx.t_net)
            extra["particles"][n] = run_all(c2, z_tr, ds, cfg.seed, log, with_online=False)
            save(extra, out / "metrics" / "extra.json")
    for nd in (8, 32):                                          # 潜空间维数消融：须重训全部网络
        if room(60 + 150 + 60, f"nd{nd}"):
            log(f"潜空间维数 n_d={nd}")
            c3, z3, info = prepare(replace(cfg, n_d=nd), ds, out, log, fresh, amort_seconds=150)
            extra["latent_dim"][nd] = {"info": info, "results": run_all(c3, z3, ds, cfg.seed, log, with_online=False)}
            save(extra, out / "metrics" / "extra.json")
    log(f"阶段乙结束，累计用时 {elapsed():.0f}s（时限 {LIMIT_ALL}s）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["a", "all"], default="all")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--set", nargs="*", default=[], help="覆盖配置项，如 n_test=200 amort_seconds=60")
    ap.add_argument("--out", default=None, help="输出子目录名（调试用），默认直接写入 outputs/")
    args = ap.parse_args()
    cfg, out = Config(), OUT
    if args.smoke:
        cfg = replace(cfg, ae_epochs=3, readout_epochs=2, amort_seconds=15, n_test=50, online_iters=10)
        out = OUT / "smoke"
    if args.out:
        out = OUT / args.out
    for item in args.set:                                       # 命令行覆盖：按配置项原有类型转换
        key, val = item.split("=")
        cfg = replace(cfg, **{key: type(getattr(cfg, key))(val)})
    (out / "figures").mkdir(parents=True, exist_ok=True)
    torch.manual_seed(cfg.seed)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    log = make_logger(out / "logs" / "run.log")
    log(f"配置: {cfg.to_dict()}")
    ds = data.load(torch.device("cuda"))
    ctx, z_tr = stage_a(cfg, ds, out, log, args.fresh)
    if args.stage == "all" and not args.smoke:
        stage_b(cfg, ds, out, log, ctx, z_tr, args.fresh)


if __name__ == "__main__":
    main()
