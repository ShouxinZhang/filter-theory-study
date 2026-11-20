"""确定性双向转换与最小差异回写引擎（TeX <-> 受控学术 Markdown）。"""
from __future__ import annotations

from .codec import MdUnit, TexUnit, Unit, md_to_tex, parse_md_units, parse_tex_units, tex_to_md
from .diffpatch import (
    PatchResult, SyncPair, check_pair_export, patch_list_minimal,
    patch_tex, run_export_cli, run_import_cli,
)
from .floats import extract_alg_standalone
from .inline import (
    BOOK_SPEC, EN_SPEC, KALMAN_SPEC, SyncSpec, grab_braced, grab_bracketed, md_inline_to_tex,
    patch_paragraph_minimal, split_sentences, strip_tex_comment, tex_inline_to_md,
)
from .manifest import (
    MANIFEST_NAME, TexSyncManifest, discover_tex_project, execute_export, execute_import,
)

__all__ = [
    "BOOK_SPEC", "EN_SPEC", "KALMAN_SPEC", "MANIFEST_NAME", "MdUnit", "PatchResult", "SyncPair",
    "SyncSpec", "TexSyncManifest", "TexUnit", "Unit", "check_pair_export",
    "discover_tex_project", "execute_export", "execute_import", "extract_alg_standalone",
    "grab_braced", "grab_bracketed", "md_inline_to_tex", "md_to_tex", "parse_md_units",
    "parse_tex_units", "patch_list_minimal", "patch_paragraph_minimal", "patch_tex",
    "run_export_cli", "run_import_cli", "split_sentences", "strip_tex_comment",
    "tex_inline_to_md", "tex_to_md",
]
