#!/usr/bin/env python3
"""毕业论文 HTML 副本薄入口：将构建与双栏实时预览统一委托给通用 html-tex-doc 技能。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_SCRIPTS = (
    next(p for p in HERE.parents if (p / ".agents/skills/chores/html-tex-doc/scripts/html_tex_doc.py").exists())
    / ".agents/skills/chores/html-tex-doc/scripts"
)


def main() -> int:
    argv = list(sys.argv[1:])
    if argv and argv[0] in ("build", "serve"):
        if len(argv) == 1 or argv[1].startswith("-"):
            argv.insert(1, str(HERE))
    os.execv(sys.executable, [sys.executable, str(SKILL_SCRIPTS / "html_tex_doc.py"), *argv])


if __name__ == "__main__":
    raise SystemExit(main())
