"""运行时资源打包：把 assets/ 下按文件名排序的分段拼成单个 style.css / reader.js / editor.js。

不引入打包工具：纯文本拼接，产物可直接被 file:// 页面引用。工程级定制的优先级：
  1. 工程 src/ 里存在同名整份文件（旧工程的做法）时原样使用；
  2. 否则使用技能内的分段，并对样式追加工程的 src/theme.css（覆盖变量）与 src/extra.css。
"""
from __future__ import annotations

from pathlib import Path

from .paths import ASSETS_DIR

_PARTS = {
    "style.css": ["css/*.css"],
    "reader.js": ["js/core.js", "js/reader/*.js"],
    "editor.js": ["js/core.js", "js/editor/*.js"],
}
_PROJECT_CSS = ("theme.css", "extra.css")


def part_files(name: str) -> list[Path]:
    files: list[Path] = []
    for pat in _PARTS[name]:
        files += sorted(ASSETS_DIR.glob(pat))
    return files


def bundle(name: str, src_dir: Path | None = None) -> str:
    if src_dir is not None and (src_dir / name).exists():
        return (src_dir / name).read_text(encoding="utf-8")
    text = "".join(f.read_text(encoding="utf-8") for f in part_files(name))
    if name == "style.css" and src_dir is not None:
        for extra in _PROJECT_CSS:
            if (src_dir / extra).exists():
                text += f"\n/* ---- 工程定制：{extra} ---- */\n" + (src_dir / extra).read_text(encoding="utf-8")
    return text


def write_site_assets(src_dir: Path, out_dir: Path) -> None:
    for name in ("style.css", "reader.js"):
        (out_dir / name).write_text(bundle(name, src_dir), encoding="utf-8")
