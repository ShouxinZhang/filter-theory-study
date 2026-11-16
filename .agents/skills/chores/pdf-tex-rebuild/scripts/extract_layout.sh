#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <pdf_abs_path> <case_dir>" >&2
  exit 1
fi

pdf_abs="$1"
case_dir="$2"

if [[ ! -f "$pdf_abs" ]]; then
  echo "PDF not found: $pdf_abs" >&2
  exit 1
fi

mkdir -p "$case_dir/meta" "$case_dir/raw" "$case_dir/parsed" "$case_dir/rebuild"

printf '%s\n' "$pdf_abs" > "$case_dir/meta/source_pdf.txt"
pdfinfo "$pdf_abs" > "$case_dir/meta/pdfinfo.txt"
{
  echo "pdfinfo: $(pdfinfo -v 2>&1 | head -n 1)"
  echo "pdftotext: $(pdftotext -v 2>&1 | head -n 1)"
  echo "pdftohtml: $(pdftohtml -v 2>&1 | head -n 1)"
  echo "python3: $(python3 --version)"
  echo "repo_root: $REPO_ROOT"
} > "$case_dir/meta/tool_versions.txt"

pdftotext -layout "$pdf_abs" "$case_dir/raw/layout.txt"
pdftotext -bbox-layout "$pdf_abs" "$case_dir/raw/bbox-layout.html"
pdftohtml -xml -nodrm "$pdf_abs" "$case_dir/raw/layout.xml" >/dev/null 2>&1

echo "Layout extracted into: $case_dir"
