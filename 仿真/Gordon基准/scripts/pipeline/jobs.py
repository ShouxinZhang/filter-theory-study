"""实验矩阵和可恢复作业，数值结果只由独立 C++ 程序产生。"""
import csv
import json
import math
import os
import subprocess
import time
from pathlib import Path
from .common import ROOT, atomic_json, digest_file, digest_object, command

def configurations(config):
    for algorithm in config["algorithms"]:
        ns = [0] if algorithm in ("kf", "ekf") else config["particles"]
        epsilons = config["epsilons"] if algorithm == "etpf" else [0]
        for n in ns:
            for epsilon in epsilons:
                for interval in config["intervals"]:
                    item = dict(algorithm=algorithm, n=n, epsilon=epsilon, interval=interval)
                    item["config_id"] = "%s_n%s_e%s_m%s" % (algorithm, n, epsilon, interval)
                    yield item

def execute_job(task):
    run_dir, dataset_dir, manifest, trial, config, cfg = task
    folder = run_dir / "jobs" / cfg["config_id"] / ("trial_%04d" % trial["trial"])
    folder.mkdir(parents=True, exist_ok=True)
    status_path = folder / "status.json"
    fingerprint = digest_object({"dataset": manifest["dataset_id"], "trial": trial,
        "configuration": cfg, "solver": config["solver"], "algorithm_seed": config["algorithm_seed"],
        "binary": digest_file(ROOT / "build/filter"), "evaluator": digest_file(ROOT / "build/evaluate")})
    if status_path.exists():
        old = json.loads(status_path.read_text())
        if old.get("state") == "complete" and old.get("fingerprint") == fingerprint:
            if all((folder / name).exists() and digest_file(folder / name) == digest
                   for name, digest in old["outputs"].items()):
                return {**old, "skipped": True}
    status = {"state": "running", "fingerprint": fingerprint, "configuration": cfg,
              "trial": trial["trial"], "folder": str(folder), "started_unix": time.time()}
    atomic_json(status_path, status)
    seed = config["algorithm_seed"] + trial["trial"]
    status["algorithm_seed"] = seed
    args = command(ROOT / "build/filter", observations=dataset_dir / trial["observations"],
        output=folder / "filter.csv", model=config["dataset"]["model"], algorithm=cfg["algorithm"],
        n=cfg["n"] or 2, epsilon=cfg["epsilon"] or 1, interval=cfg["interval"], seed=seed,
        tolerance=config["solver"]["tolerance"], max_iterations=config["solver"]["max_iterations"])
    if trial["trial"] == 0 and config.get("snapshots", False):
        args.extend(["--snapshot", str(folder / "particles.csv")])
    environment = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    try:
        with (folder / "log.txt").open("w") as log:
            subprocess.run(args, check=True, text=True, stdout=log, stderr=log, env=environment)
            subprocess.run(command(ROOT / "build/evaluate", truth=dataset_dir / trial["truth"],
                filter=folder / "filter.csv", output=folder / "metrics.csv",
                common_interval=math.lcm(*config["intervals"])), check=True, text=True,
                stdout=log, stderr=log, env=environment)
        output_names = ["filter.csv", "filter.csv.runtime.csv", "metrics.csv"]
        if (folder / "particles.csv").exists():
            output_names.append("particles.csv")
        status.update(state="complete", outputs={n: digest_file(folder / n) for n in output_names})
    except Exception as error:
        status.update(state="failed", error=str(error))
    status["finished_unix"] = time.time()
    atomic_json(status_path, status)
    return status

def write_index(run_dir, statuses):
    """失败作业显式保留在状态清单，不向汇总器提供不存在的数值。"""
    path = run_dir / "index.csv"
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["config_id", "algorithm", "n", "epsilon", "interval", "trial", "metrics_path"])
        for item in sorted(statuses, key=lambda s: (s["configuration"]["config_id"], s["trial"])):
            if item["state"] == "complete":
                c = item["configuration"]
                writer.writerow([c[k] for k in ("config_id", "algorithm", "n", "epsilon", "interval")]
                                + [item["trial"], str(Path(item["folder"]) / "metrics.csv")])
    return path
