"""采集真实环境并查找已有绘图环境，不创建重复虚拟环境。"""
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from .common import ROOT, digest_file

def capture(args):
    p = subprocess.run(args, text=True, capture_output=True)
    return p.stdout.strip() if p.returncode == 0 else p.stderr.strip()

def plotting_python():
    candidates = [os.environ.get("BASELINE_PLOT_PYTHON"), sys.executable,
                  str(Path.home() / "Documents/GitHub/.shared-python-envs/py312-torch-cu130/bin/python"),
                  "/usr/bin/python3"]
    for candidate in dict.fromkeys(filter(None, candidates)):
        if Path(candidate).exists():
            test = subprocess.run([candidate, "-c", "import matplotlib,numpy"], capture_output=True)
            if test.returncode == 0:
                return candidate
    raise RuntimeError("未找到 matplotlib/numpy 环境，请设置 BASELINE_PLOT_PYTHON")

def collect(jobs, plot_python):
    memory = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        if key in ("MemTotal", "MemAvailable", "SwapTotal"):
            memory[key + "_kib"] = int(value.split()[0])
    cpu = json.loads(capture(["lscpu", "-J"]))["lscpu"]
    cpu_fields = {item["field"].rstrip(":"): item["data"] for item in cpu}
    versions = capture([plot_python, "-c",
        "import sys,numpy,matplotlib,json;print(json.dumps({'python':sys.version,'numpy':numpy.__version__,'matplotlib':matplotlib.__version__}))"])
    cache = (ROOT / "build/CMakeCache.txt").read_text()
    cmake = {line.split("=", 1)[0]: line.split("=", 1)[1] for line in cache.splitlines()
             if "=" in line and (line.startswith("CMAKE_CXX_COMPILER:") or line.startswith("CMAKE_CXX_FLAGS"))}
    eigen_header = Path("/usr/include/eigen3/Eigen/src/Core/util/Macros.h")
    eigen_version = ".".join(re.search(r"#define EIGEN_" + part + r"_VERSION\s+(\d+)", eigen_header.read_text())[1]
                            for part in ("WORLD", "MAJOR", "MINOR")) if eigen_header.exists() else "见CMake依赖"
    return {"cpu": cpu_fields, "memory": memory, "eigen_version": eigen_version, "os_release": Path("/etc/os-release").read_text(),
            "kernel": platform.release(), "compiler": capture(["c++", "--version"]),
            "cmake": capture(["cmake", "--version"]), "compile_options": cmake,
            "affinity": sorted(os.sched_getaffinity(0)), "parallel_jobs": jobs, "threads_per_filter": 1,
            "timing_mode": "串行无本任务内争用" if jobs == 1 else "并行精度实验，不作为严格速度基准",
            "plotting_python": plot_python, "plotting_versions": json.loads(versions),
            "executables": {n: digest_file(ROOT / "build" / n) for n in ("generate", "filter", "evaluate", "summarize")},
            "numeric_rules": "IEEE double，Eigen单线程，未开启fast-math"}
