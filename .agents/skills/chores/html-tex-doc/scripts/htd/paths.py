"""技能目录内各类资源的位置。"""
from __future__ import annotations

from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
SKILL_ROOT = SCRIPTS_DIR.parent
ASSETS_DIR = SKILL_ROOT / "assets"

TEMPLATE_BASIC = SKILL_ROOT / "references" / "templates" / "src"
TEMPLATE_ACADEMIC = SKILL_ROOT / "references" / "templates" / "academic-md" / "src"
TEMPLATE_SRC = TEMPLATE_BASIC  # 向后兼容旧常量名


def _resolve_asset(src_dir: Path, filename: str) -> Path:
    """工程 src/ 内的同名文件优先，否则取 basic 模板里的公共文件（TeX 公共导言、默认宏等）。"""
    p = src_dir / filename
    return p if p.exists() else TEMPLATE_BASIC / filename
