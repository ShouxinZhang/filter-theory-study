#!/usr/bin/env python3
"""调度独立 C++ 网格参考与评价，保留来源和可恢复检查点。"""
import argparse
import csv
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from pipeline.common import ROOT, atomic_json, command, digest_file, digest_object


def compute(manifest, output, bound, spacing, interval):
    directory = output / ("m%d_L%g_dx%g" % (interval, bound, spacing))
    directory.mkdir(parents=True, exist_ok=True)
    trials = manifest["trials"]
    dataset_dir = Path(manifest["directory"])
    # 核对冻结输入，引用输出不覆盖原基线运行。
    for trial in trials:
        for field in ("truth", "observations"):
            assert digest_file(dataset_dir / trial[field]) == trial[field + "_sha256"]
    source = {str(p.relative_to(ROOT)): digest_file(p) for p in (
        ROOT / "build/grid_reference", ROOT / "build/grid_risk", ROOT / "src/reference/grid_reference.cpp",
        ROOT / "include/baseline/grid_reference.hpp", ROOT / "apps/grid_reference.cpp", ROOT / "apps/grid_risk.cpp",
        ROOT / "src/models/model.cpp", ROOT / "scripts/grid_reference.py")}
    identity = digest_object({"manifest": manifest, "source": source, "bound": bound, "spacing": spacing, "interval": interval})
    status_path = directory / "status.json"
    if status_path.exists():
        status = json.loads(status_path.read_text())
        if status["identity"] == identity and all((directory / p).exists() and digest_file(directory / p) == sha for p, sha in status["outputs"].items()):
            print(directory.name, "恢复跳过", flush=True)
            return directory
    index = directory / "observations_index.csv"
    index.write_text("observations_path\n" + "".join(str(dataset_dir / t["observations"]) + "\n" for t in trials))
    start = time.monotonic()
    subprocess.run(command(ROOT / "build/grid_reference", index=index, output=directory,
        model=manifest["spec"]["model"], bound=bound, spacing=spacing, interval=interval), check=True)
    evaluation = directory / "evaluation_index.csv"
    with evaluation.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["truth_path", "filter_path"])
        for b, trial in enumerate(trials):
            writer.writerow([dataset_dir / trial["truth"], directory / ("trial_%04d" % b) / "filter.csv"])
    subprocess.run(command(ROOT / "build/grid_risk", index=evaluation, output=directory / "risk.csv"), check=True)
    outputs = [directory / "risk.csv", directory / "risk.csv.ci.csv", directory / "diagnostics.csv"] + list(directory.glob("trial_*/filter.csv"))
    atomic_json(status_path, {"identity": identity, "source": source, "seconds": time.monotonic()-start,
        "outputs": {str(p.relative_to(directory)): digest_file(p) for p in outputs}})
    print(directory.name, "完成，秒数", time.monotonic()-start, flush=True)
    return directory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--cases", default="60:0.2,60:0.1,60:0.05,80:0.05")
    parser.add_argument("--interval", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text())
    output = Path(args.output).resolve(); output.mkdir(parents=True, exist_ok=True)
    cases = [tuple(map(float, case.split(":"))) for case in args.cases.split(",")]
    atomic_json(output / "dataset.json", manifest)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(lambda pair: compute(manifest, output, *pair, args.interval), cases))

if __name__ == "__main__":
    main()
