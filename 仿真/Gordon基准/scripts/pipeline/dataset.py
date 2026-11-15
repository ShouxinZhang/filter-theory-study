"""构造只读基准，逐轨迹原子提交，恢复时检查内容哈希。"""
import json
import os
import shutil
from .common import ROOT, digest_object, digest_file, atomic_json, command, run_checked

def ensure_dataset(spec):
    identity = {"spec": spec, "generator": digest_file(ROOT / "build/generate"), "format": 1}
    key = digest_object(identity)[:16]
    directory = ROOT / "data" / key
    manifest_path = directory / "manifest.json"
    directory.mkdir(parents=True, exist_ok=True)
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for item in manifest["trials"]:
            for name in ("observations", "truth"):
                path = directory / item[name]
                if not path.exists() or digest_file(path) != item[name + "_sha256"]:
                    raise RuntimeError("冻结基准内容变更: " + str(path))
        return directory, manifest
    trials = []
    for trial in range(spec["trials"]):
        target = directory / ("trial_%04d" % trial)
        seed = spec["seed"] + trial
        if not target.exists():
            temp = directory / (target.name + ".staging")
            if temp.exists():
                shutil.rmtree(temp)  # 仅清理本生成器尚未提交的暂存数据
            temp.mkdir()
            run_checked(command(ROOT / "build/generate", model=spec["model"], steps=spec["steps"],
                seed=seed, fixed_initial=int(spec.get("fixed_initial", False)),
                observations=temp / "observations.csv", truth=temp / "truth.csv"))
            os.replace(temp, target)
        item = {"trial": trial, "seed": seed}
        for name, filename in (("observations", "observations.csv"), ("truth", "truth.csv")):
            path = target / filename
            item[name] = str(path.relative_to(directory))
            item[name + "_sha256"] = digest_file(path)
        trials.append(item)
    manifest = {"dataset_id": key, **identity, "trials": trials}
    atomic_json(manifest_path, manifest)
    return directory, manifest
