"""只组装文件索引，所有时序误差计算交给 C++。"""
import csv
import json
import subprocess
from pathlib import Path
from .common import ROOT, atomic_json, digest_file, command

def refresh_time_series(run_dir):
    run_dir = Path(run_dir)
    dataset = json.loads((run_dir / "dataset.json").read_text())
    jobs = json.loads((run_dir / "jobs.json").read_text())
    trials = {item["trial"]: item for item in dataset["trials"]}
    dataset_dir = Path(dataset["directory"])
    # 核对冻结真值，避免旧输出和被修改的基准混用
    for trial in trials.values():
        truth = dataset_dir / trial["truth"]
        if digest_file(truth) != trial["truth_sha256"]:
            raise RuntimeError("时序评估真值哈希不匹配: " + str(truth))
    index = run_dir / "time_series_index.csv"
    with index.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["config_id", "algorithm", "n", "epsilon", "interval",
                         "trial", "truth_path", "filter_path"])
        for job in sorted(jobs, key=lambda j: (j["configuration"]["config_id"], j["trial"])):
            if job["state"] != "complete":
                continue
            cfg = job["configuration"]
            # 以运行目录定位输出，不依赖生成时的绝对路径
            output = run_dir / "jobs" / cfg["config_id"] / ("trial_%04d" % job["trial"]) / "filter.csv"
            if digest_file(output) != job["outputs"]["filter.csv"]:
                raise RuntimeError("时序评估滤波输出哈希不匹配: " + str(output))
            writer.writerow([cfg[k] for k in ("config_id", "algorithm", "n", "epsilon", "interval")] +
                [job["trial"], dataset_dir / trials[job["trial"]]["truth"], output.resolve()])
    executable = ROOT / "build/time_series"
    if not executable.exists():
        raise RuntimeError("请先使用 CMake 构建 time_series 评估程序")
    subprocess.run(command(executable, index=index, output=run_dir / "time_series.csv"), check=True)
    # 旧滤波源码快照保持不变，补充评估版本单独记录
    atomic_json(run_dir / "time_series_metadata.json", {
        "definition": "rmse[k]=sqrt(mean_b((estimate[b,k]-truth[b,k])^2))",
        "cumulative_definition": "cumulative_rmse[k]=sqrt(mean_b,t<=k(error[b,t]^2))",
        "executable_sha256": digest_file(executable),
        "index_sha256": digest_file(index), "result_sha256": digest_file(run_dir / "time_series.csv"),
        "source": {str(p.relative_to(ROOT)): digest_file(p) for p in (
            ROOT / "src/evaluation/time_series.cpp", ROOT / "include/baseline/time_series.hpp",
            ROOT / "apps/time_series.cpp", ROOT / "scripts/pipeline/time_series.py")}
    })
