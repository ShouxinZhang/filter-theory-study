"""路径，哈希及原子状态更新，不处理滤波数值。"""
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def digest_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def digest_object(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    os.replace(temporary, path)

def command(executable, **kwargs):
    args = [str(executable)]
    for key, value in kwargs.items():
        args.extend(["--" + key.replace("_", "-"), str(value)])
    return args

def run_checked(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)

def source_files():
    paths = [ROOT / "CMakeLists.txt"]
    for folder in ("include", "src", "apps", "scripts", "tests", "templates"):
        paths.extend(p for p in (ROOT / folder).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    return sorted(paths)

def source_hash():
    return digest_object({str(p.relative_to(ROOT)): digest_file(p) for p in source_files()})
