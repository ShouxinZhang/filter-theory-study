#!/usr/bin/env python3
r"""无分页 HTML / 受控 Markdown 正文 + TeX standalone 出图/算法 的混合文档构建与实时预览工具。

仅依赖 Python 标准库 + TeX Live / dvisvgm。

子命令：
  init <dir> [--title 标题] [--preset basic|academic-md] [--force]
      从技能内置模板初始化 <dir>/src/ 骨架工程。
  build [dir] [--src DIR] [--build-dir DIR] [--out DIR] [--force]
      解析 src/*.md（或 src/doc.html）分配唯一编号 -> 生成 labels.tex -> xelatex/dvisvgm 编译 SVG
      -> 输出单页静态站点（index.html + style.css + reader.js + 静态图资源）。
  serve [dir] [--src DIR] [--build-dir DIR] [--out DIR] [--port 18767] [--host 127.0.0.1]
      启动本地实时预览与类 VS Code 双栏编辑服务（支持局部 MathJax 热刷新、全文搜索与正反向行级高亮对齐）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from htd.build import build_project  # noqa: E402,F401  供外部脚本沿用旧的导入方式
from htd.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
