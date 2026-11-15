"""以作者官方代码作为 OTPF 对照。

官方仓库：https://github.com/Mohd9485/Filtering-with-Optimal-Transport （Static MNIST/OT.py）。
本脚本不修改官方源码，直接调用其 OT() 函数；网络结构、损失、优化器与超参数全部取官方 main.py 的设置。
只替换问题本身的输入：还原算子（官方为生成对抗网络的生成器）、观测函数、观测序列与初始粒子。
官方实现固定在 CPU 上运行且一次处理一幅图像，故用多进程并行处理若干幅测试图像。

状态：接线测试通过，但完整运行（每幅图像单核约十余分钟）未跑完即被中止，
因此没有可用结果，论文中也未使用。保留本脚本只为便于日后补做该对照。

须先把官方仓库克隆到 third_party/ 下（见 README）。

用法：python -I official_otpf.py --count 28 --workers 28
"""
import argparse
import contextlib
import importlib.util
import io
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                                  # -I 模式下须显式加入本包路径

import numpy as np
import torch

from latent_filter.config import OUT, ROOT, Config

OFFICIAL = ROOT / "third_party" / "Filtering-with-Optimal-Transport" / "Static MNIST" / "OT.py"


def official_parameters(cfg, n_particles, iteration):
    """官方 Static MNIST/main.py 中的网络与训练超参数，原样照搬。"""
    return {
        "normalization": "None",
        "NUM_NEURON": 32 * 10,
        "SAMPLE_SIZE": n_particles,
        "BATCH_SIZE": 64,
        "LearningRate": 1e-3,
        "ITERATION": iteration,                                # 官方为 1024
        "Final_Number_ITERATION": 64 * 16 * 4,
        "INPUT_DIM": [cfg.n_d, cfg.window ** 2],
    }


def worker(job):
    """子进程：对一幅图像调用官方 OT()，返回各步粒子 [K, J, n_d] 与耗时。"""
    index, z0, y_full, cfg, iteration, particle_noise = job
    torch.set_num_threads(1)
    torch.manual_seed(1000 + index)
    np.random.seed(1000 + index)
    spec = importlib.util.spec_from_file_location("official_ot", OFFICIAL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    model = torch.load(OUT / "checkpoints" / f"compress_restore_nd{cfg.n_d}.pt", weights_only=False, map_location="cpu")

    class Restore(torch.nn.Module):                            # 官方接口中的 A：潜变量 -> 图像
        def forward(self, z):
            return model.restore(z)

    w, g = cfg.window, 28 // cfg.window
    h_index = torch.tensor([[(k // g) * w, (k % g) * w] for k in range(cfg.n_steps)])

    def h(img, corner):                                        # 官方接口中的 h：取出窗口内像素
        r0, c0 = int(corner[0]), int(corner[1])
        return img[:, r0:r0 + w, c0:c0 + w].reshape(img.shape[0], -1)

    y_img = torch.from_numpy(y_full).view(1, 28, 28)
    y_seq = torch.stack([h(y_img, c)[0] for c in h_index])[None]          # [1, K, r^2]
    x_dummy = torch.zeros(1, 1, cfg.n_d)                       # 官方只用到其形状
    noise = [0.0, particle_noise, 0.0, cfg.sigma, 0.0]         # [未用, 粒子人工噪声, 未用, 观测噪声, 未用]
    t0 = time.time()
    with contextlib.redirect_stdout(io.StringIO()):
        out = mod.OT(x_dummy, y_seq, z0.T[None].astype(np.float64), official_parameters(cfg, z0.shape[0], iteration),
                     Restore(), h, None, 1, noise, h_index, w)
    return index, out[0, 1:].transpose(0, 2, 1).astype(np.float32), time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=28, help="测试图像数（取测试集最前面的若干幅）")
    ap.add_argument("--workers", type=int, default=28)
    ap.add_argument("--particles", type=int, default=256)
    ap.add_argument("--iteration", type=int, default=1024, help="官方值 1024；仅调试时改小")
    ap.add_argument("--particle-noise", type=float, default=0.1, help="官方每步加在粒子上的人工噪声标准差")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    import multiprocessing as mp
    from latent_filter import data
    from latent_filter.evaluate import Context, evaluate, make_inputs, step_metrics
    from latent_filter.observe import window_masks
    from run import prepare, runners

    cfg = replace(Config(), n_particles=args.particles)
    ds = data.load(torch.device("cuda"))
    ctx, z_tr, _ = prepare(cfg, ds, OUT, print, False)        # 读取主实验的检查点
    # 与主实验完全相同的初始粒子与观测噪声（同一随机种子、同样取前 500 幅后截取）
    x_all, lab_all = ds[2][:cfg.n_test], ds[3][:cfg.n_test]
    z0_all, y_all = make_inputs(cfg, z_tr, x_all, cfg.seed)
    x, lab, z0, y_full = x_all[:args.count], lab_all[:args.count], z0_all[:args.count], y_all[:args.count]

    jobs = [(i, z0[i].cpu().numpy(), y_full[i].cpu().numpy(), cfg, args.iteration, args.particle_noise)
            for i in range(args.count)]
    t0 = time.time()
    with mp.get_context("spawn").Pool(args.workers) as pool:
        done = pool.map(worker, jobs, chunksize=1)
    wall = time.time() - t0
    done.sort(key=lambda d: d[0])
    parts = torch.from_numpy(np.stack([d[1] for d in done])).cuda()       # [B, K, J, n_d]
    secs = [d[2] for d in done]

    res = {}
    for k in range(cfg.n_steps):                               # 与其他方法相同的指标
        for name, v in step_metrics(ctx, parts[:, k], x, lab).items():
            res.setdefault(name, []).append(v.mean().item())
    res["per_image_final_correct"] = step_metrics(ctx, parts[:, -1], x, lab)["acc"].tolist()
    res["cpu_seconds_per_image"] = secs
    res["time"] = [sum(secs) / len(secs) / cfg.n_steps] * cfg.n_steps     # 每图每步（单核 CPU）

    # 同一批图像、同一批初始粒子上的其他方法，供逐项对照
    others = {name: evaluate(ctx, fn, z0, y_full, x, lab) for name, fn in runners(cfg).items()}
    out = {"count": args.count, "particles": args.particles, "iteration": args.iteration,
           "particle_noise": args.particle_noise, "wall_seconds": wall,
           "official_otpf": res, "others_same_subset": others}
    path = OUT / "metrics" / f"official_otpf_N{args.particles}{args.tag}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"官方 OTPF: {args.count} 幅, 墙钟 {wall:.0f}s, 每图 CPU {sum(secs) / len(secs):.0f}s")
    print("  官方 OTPF  acc@4,8,12,16 =", [round(res["acc"][k], 3) for k in (3, 7, 11, 15)])
    for name, r in others.items():
        print(f"  {name:11s} acc@4,8,12,16 =", [round(r["acc"][k], 3) for k in (3, 7, 11, 15)])


if __name__ == "__main__":
    main()
