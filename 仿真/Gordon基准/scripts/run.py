#!/usr/bin/env python3
"""构建，调度 C++ 数据/滤波/评估入口，最后调用绘图和报告脚本。"""
import argparse
import concurrent.futures
import datetime
import json
import shutil
import sys
import time
from pipeline.common import ROOT, atomic_json, digest_object, source_hash, source_files, run_checked, command
from pipeline.dataset import ensure_dataset
from pipeline.environment import collect, plotting_python
from pipeline.jobs import configurations, execute_job, write_index

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/smoke.json")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs 必须为正")
    config_path = ROOT / args.config
    config = json.loads(config_path.read_text())
    if not args.skip_build:
        run_checked(["cmake", "-S", str(ROOT), "-B", str(ROOT / "build"), "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release"])
        run_checked(["cmake", "--build", str(ROOT / "build"), "-j", "8"])
        run_checked(["ctest", "--test-dir", str(ROOT / "build"), "--output-on-failure"])
    for field in ("steps", "trials"):
        if config["dataset"][field] < 1:
            raise ValueError("数据集规模必须为正")
    if min(config["particles"]) < 2 or min(config["intervals"]) < 1 or min(config["epsilons"]) <= 0:
        raise ValueError("实验参数无效")
    plot_python = plotting_python()
    digest = source_hash()
    env = collect(args.jobs, plot_python)
    identity = {"configuration": config, "source": digest, "jobs": args.jobs,
                "binaries": env["executables"], "affinity": env["affinity"],
                "cpu_model": env["cpu"].get("Model name")}
    run_id = config_path.stem + "-" + digest_object(identity)[:12]
    run_dir = ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = run_dir / "metadata.json"
    if not metadata_path.exists():
        atomic_json(metadata_path, {"run_id": run_id, "created": datetime.datetime.now().astimezone().isoformat(),
            **identity, "environment": env})
        for p in source_files():
            target = run_dir / "source" / p.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
    atomic_json(run_dir / "session_environment.json", env)
    atomic_json(run_dir / "config.json", config)
    dataset_dir, manifest = ensure_dataset(config["dataset"])
    atomic_json(run_dir / "dataset.json", {"directory": str(dataset_dir), **manifest})
    tasks = [(run_dir, dataset_dir, manifest, trial, config, cfg)
             for cfg in configurations(config) for trial in manifest["trials"]]
    print("运行目录:", run_dir, flush=True)
    print("作业数:", len(tasks), "并发:", args.jobs, flush=True)
    statuses = []
    start = last = time.monotonic()
    # 恢复粒度为一条轨迹，每个状态文件原子写入
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs)
    futures = [executor.submit(execute_job, task) for task in tasks]
    try:
        for future in concurrent.futures.as_completed(futures):
            statuses.append(future.result())
            now = time.monotonic()
            if now - last > 10 or len(statuses) == len(tasks):
                print("完成 %s/%s，失败 %s，用时 %.1fs" %
                      (len(statuses), len(tasks), sum(s["state"] == "failed" for s in statuses), now - start), flush=True)
                last = now
    except KeyboardInterrupt:
        # 取消尚未开始的任务，已提交的逐轨迹状态支持下一次恢复
        executor.shutdown(wait=True, cancel_futures=True)
        print("已中断，完成轨迹的检查点已保留", flush=True)
        return 130
    else:
        executor.shutdown(wait=True)
    atomic_json(run_dir / "jobs.json", statuses)
    index = write_index(run_dir, statuses)
    run_checked(command(ROOT / "build/summarize", index=index, output=run_dir / "summary.csv",
                        bootstrap=config.get("bootstrap", 1000)))
    atomic_json(run_dir / "execution.json", {"seconds": time.monotonic() - start,
        "expected_jobs": len(tasks), "complete_jobs": sum(s["state"] == "complete" for s in statuses),
        "failed_jobs": sum(s["state"] == "failed" for s in statuses),
        "skipped_jobs": sum(s.get("skipped", False) for s in statuses)})
    run_checked([plot_python, str(ROOT / "scripts/report.py"), str(run_dir)])
    (ROOT / "runs/LATEST").write_text(run_id + "\n")
    print("报告:", run_dir / "report.md", flush=True)
    return 1 if any(s["state"] == "failed" for s in statuses) else 0

if __name__ == "__main__":
    sys.exit(main())
