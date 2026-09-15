"""Package the complete workspace and the author's built talk for Windows.
Run after build/PDF/PPTX exports: python scripts/package-release.py
Uses Python standard library only. Does not include OS-specific node_modules.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {"node_modules", ".git", ".slidev", ".drawio-history", ".slide-order-history", ".image-paste-history", "__pycache__", "validation", "releases"}
for relative in ["talks/filtering/dist/index.html", "talks/filtering/output/academic.pdf", "talks/filtering/output/academic.pptx", "runtime/win-x64/node.exe", "runtime/win-arm64/node.exe", "启动汇报.cmd"]:
    if not (ROOT / relative).is_file():
        raise SystemExit(f"Missing {relative}; build and export the talk first.")
files = []
for path in ROOT.rglob("*"):
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDE for part in relative.parts):
        continue
    if path.is_symlink():
        raise SystemExit(f"Symbolic links are not portable: {relative}")
    if path.is_file():
        if "dist" in relative.parts or "output" in relative.parts:
            if relative.parts[:2] != ("talks", "filtering"):
                continue
        files.append((path, relative.as_posix()))
release = ROOT / "releases"
release.mkdir(exist_ok=True)
now = datetime.now().astimezone()
archive = release / f"filtering-win11-offline-{now:%Y-%m-%d_%H%M%S}.zip"
manifest = {"created": now.isoformat(), "format": "one-click offline Windows presentation + bundled x64/ARM64 runtime + editable source", "files": {}}
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for path, relative in sorted(files, key=lambda item: item[1]):
        data = path.read_bytes()
        manifest["files"][relative] = hashlib.sha256(data).hexdigest()
        info = zipfile.ZipInfo.from_file(path, arcname="filtering-win11-offline/" + relative)
        z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
    z.writestr("filtering-win11-offline/BUNDLE-MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
with zipfile.ZipFile(archive) as z:
    if z.testzip() is not None:
        raise SystemExit("Archive verification failed")
checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix(".zip.sha256").write_text(f"{checksum}  {archive.name}\n", encoding="utf-8")
print(f"{archive} ({archive.stat().st_size / 1024**2:.1f} MiB; {len(files)} files)")
