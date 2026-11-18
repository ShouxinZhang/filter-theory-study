#!/usr/bin/env python3
"""Kalman (1960) 逆向回写薄适配脚本：html/src/*.md -> sections/*.tex。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

try:
    from htd.texsync import KALMAN_SPEC, SyncPair, grab_braced, run_export_cli, tex_inline_to_md
except ModuleNotFoundError:
    for _anc in (HERE, *HERE.parents):
        _cand = _anc / ".agents/skills/chores/html-tex-doc/scripts"
        if _cand.is_dir():
            sys.path.insert(0, str(_cand))
            break
    from htd.texsync import KALMAN_SPEC, SyncPair, grab_braced, run_export_cli, tex_inline_to_md


def _frame_from_main_tex(main_tex: Path) -> tuple[str, str]:
    src = main_tex.read_text(encoding="utf-8")
    m_t = re.search(r"\\newcommand\{\\htdtitle\}", src)
    m_s = re.search(r"\\newcommand\{\\htdsubtitle\}", src)
    h1 = tex_inline_to_md(grab_braced(src, m_t.end())[0], KALMAN_SPEC) if m_t else ""
    sub = tex_inline_to_md(grab_braced(src, m_s.end())[0], KALMAN_SPEC) if m_s else ""
    plain_t = re.sub(r"\[\^\w+\]", "", h1).strip()
    incs = [m.group(1) for m in re.finditer(r"\\input\{sections/([^}]+)\}", src) if m.group(1) != "abstract"]
    head = (
        f"---\ntitle: {plain_t}\nmacros: macros.tex\nbib: refs.bib\nbib_order: file\n---\n\n"
        f'<header class="title">\n<h1>{h1}</h1>\n<p class="subtitle">{sub}</p>\n</header>'
    )
    tail = "<!--TOC-->\n\n" + "\n".join(f"<!--include {name}.md-->" for name in incs) + "\n"
    return head, tail


SECTIONS = [
    "00_导读与符号约定",
    "01_最优估计与正交投影",
    "02_随机过程模型与滤波解",
    "03_对偶问题与应用算例",
    "04_参考文献与附录",
    "05_校勘记",
]

PAIRS = [
    SyncPair(
        tex_path=ROOT / "sections/abstract.tex",
        md_path=HERE / "src/main.md",
        md_slice=("</header>", "<!--TOC-->"),
        expected_md_frame=_frame_from_main_tex(ROOT / "main.tex"),
    ),
    *[SyncPair(tex_path=ROOT / f"sections/{s}.tex", md_path=HERE / f"src/{s}.md") for s in SECTIONS],
]

if __name__ == "__main__":
    raise SystemExit(run_export_cli(PAIRS, KALMAN_SPEC))
