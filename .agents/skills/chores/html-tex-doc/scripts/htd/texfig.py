"""TeX standalone 图/算法 → SVG 的增量编译。"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path

from .paths import TEMPLATE_BASIC, _resolve_asset

TEX_DEPS = ["common.tex", "macros.tex", "algcommon.tex", "alg2e.tex"]
# 改动 xelatex / dvisvgm 的调用参数时同步改这个串，使旧缓存失效
TOOLCHAIN = "xelatex -no-pdf + pgfsys-dvisvgm | dvisvgm --no-fonts --exact-bbox --currentcolor --linkmark=none --zoom=1.3 | v1"


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, errors="replace")
    return r.returncode, r.stdout + r.stderr


def cache_key(src: Path, src_dir: Path, build_dir: Path) -> str:
    """出图缓存键：只由内容决定，不看文件修改时间。

    成分：工具链参数、图源、公共导言文件、图源直接 \\input 的工程内文件、
    以及该图 \\cref 引用到的那几条编号（而非整份 labels.tex——无关编号变化不触发重编）。
    """
    h = hashlib.sha256(TOOLCHAIN.encode())
    text = src.read_text(encoding="utf-8", errors="replace")
    h.update(text.encode())
    for d in TEX_DEPS:
        p = _resolve_asset(src_dir, d)
        h.update(b"\0" + d.encode() + b"\0" + (p.read_bytes() if p.exists() else b"-"))
    for inc in sorted(set(re.findall(r"\\input\{([^}]+)\}", text))):
        for base in (src.parent, src_dir):
            p = base / (inc if inc.endswith(".tex") else inc + ".tex")
            if p.exists() and p.name not in TEX_DEPS:
                h.update(b"\0" + inc.encode() + b"\0" + p.read_bytes())
                break
    labels = build_dir / "labels.tex"
    table = {}
    if labels.exists():
        for line in labels.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\\lbl\{([^}]*)\}", line)
            if m:
                table[m.group(1)] = line
    for ref in sorted(set(re.findall(r"\\cref\{([^}]+)\}", text))):
        h.update(b"\0" + table.get(ref, "MISSING:" + ref).encode())
    return h.hexdigest()


def compile_tex(rel: str, src_dir: Path, build_dir: Path, force: bool, errors: list[str]) -> str | None:
    src = src_dir / rel
    if not src.exists():
        errors.append(f"找不到 TeX 源：{rel}")
        return None
    name = rel.replace("/", "-").removesuffix(".tex")
    wd = build_dir / "tex" / name
    wd.mkdir(parents=True, exist_ok=True)
    svg = wd / f"{name}.svg"

    key = cache_key(src, src_dir, build_dir)
    key_file = wd / f"{name}.key"
    if not force and svg.exists() and key_file.exists() and key_file.read_text(encoding="utf-8") == key:
        return svg.read_text(encoding="utf-8")
    n_err = len(errors)

    env = dict(
        os.environ,
        TEXINPUTS=f"{src_dir.resolve()}//:{build_dir.resolve()}:{TEMPLATE_BASIC.resolve()}//:",
    )
    entry = r"\def\pgfsysdriver{pgfsys-dvisvgm.def}\input{" + str(src.resolve()) + "}"
    code, out = _run(
        [
            "xelatex",
            "-no-pdf",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={wd.resolve()}",
            f"-jobname={name}",
            entry,
        ],
        cwd=src.parent,
        env=env,
    )
    log_file = wd / f"{name}.log"
    log = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else out
    if code != 0:
        tail = "\n".join(l for l in log.splitlines() if l.startswith("!") or l.startswith("l."))[:800]
        errors.append(f"xelatex 失败：{rel}\n{tail or out[-600:]}")
        return None
    for key in re.findall(r"UNDEFINED-REF: (\S+)", log):
        errors.append(f"TeX 侧未定义引用：{key}（{rel}）")

    code, out = _run(
        [
            "dvisvgm",
            "--no-fonts",
            "--exact-bbox",
            "--currentcolor",
            "--linkmark=none",
            "--zoom=1.3",
            "-o",
            str(svg.resolve()),
            str((wd / f"{name}.xdv").resolve()),
        ],
        cwd=wd,
    )
    if code != 0 or not svg.exists():
        errors.append(f"dvisvgm 失败：{rel}\n{out[-800:]}")
        return None
    if len(errors) == n_err:  # 有未定义引用等问题时不记缓存，下次构建继续报错
        key_file.write_text(key, encoding="utf-8")
    elif key_file.exists():
        key_file.unlink()
    return svg.read_text(encoding="utf-8")
