#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"

usage() {
  echo "Usage: $0 <pdf_path> [case_name]" >&2
  exit 1
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
fi

for tool in pdfinfo pdftotext pdftohtml python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing required tool: $tool" >&2
    exit 1
  fi
done

pdf_input="$1"
case_name="${2:-$(basename "${pdf_input%.*}")}"

if [[ ! -f "$pdf_input" ]]; then
  echo "PDF not found: $pdf_input" >&2
  exit 1
fi

pdf_abs="$(cd "$(dirname "$pdf_input")" && pwd)/$(basename "$pdf_input")"
case_dir="${PDF_TEX_OUT_DIR:-$REPO_ROOT/.agents/.tmp/task/pdf-tex-rebuild/$case_name}"

mkdir -p "$case_dir"

bash "$SCRIPT_DIR/extract_layout.sh" "$pdf_abs" "$case_dir"
bash "$SCRIPT_DIR/scan_references.sh" "$case_dir"
bash "$SCRIPT_DIR/render_stub.sh" "$case_dir"

echo "Build complete: $case_dir"
