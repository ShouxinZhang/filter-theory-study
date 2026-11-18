#!/usr/bin/env python3
"""Kalman (1960) 正向导入薄适配脚本：sections/*.tex -> html/src/*.md。"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

try:
    from htd.texsync import KALMAN_SPEC, SyncPair, run_import_cli
except ModuleNotFoundError:
    for _anc in (HERE, *HERE.parents):
        _cand = _anc / ".agents/skills/chores/html-tex-doc/scripts"
        if _cand.is_dir():
            sys.path.insert(0, str(_cand))
            break
    from htd.texsync import KALMAN_SPEC, SyncPair, run_import_cli

PAIRS = [
    SyncPair(
        tex_path=ROOT / "sections/abstract.tex",
        md_path=HERE / "src/main.md",
        md_slice=("</header>", "<!--TOC-->"),
    ),
    SyncPair(
        tex_path=ROOT / "sections/00_导读与符号约定.tex",
        md_path=HERE / "src/00_导读与符号约定.md",
    ),
    SyncPair(
        tex_path=ROOT / "sections/01_最优估计与正交投影.tex",
        md_path=HERE / "src/01_最优估计与正交投影.md",
    ),
    SyncPair(
        tex_path=ROOT / "sections/02_随机过程模型与滤波解.tex",
        md_path=HERE / "src/02_随机过程模型与滤波解.md",
    ),
    SyncPair(
        tex_path=ROOT / "sections/03_对偶问题与应用算例.tex",
        md_path=HERE / "src/03_对偶问题与应用算例.md",
    ),
    SyncPair(
        tex_path=ROOT / "sections/04_参考文献与附录.tex",
        md_path=HERE / "src/04_参考文献与附录.md",
    ),
    SyncPair(
        tex_path=ROOT / "sections/05_校勘记.tex",
        md_path=HERE / "src/05_校勘记.md",
    ),
]

if __name__ == "__main__":
    raise SystemExit(run_import_cli(PAIRS, KALMAN_SPEC))
