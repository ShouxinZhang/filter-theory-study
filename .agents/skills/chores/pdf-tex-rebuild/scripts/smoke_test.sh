#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <pdf_path>" >&2
  exit 1
fi

pdf_path="$1"
case_name="smoke-$(basename "${pdf_path%.*}")"
case_dir="${PDF_TEX_OUT_DIR:-$REPO_ROOT/.agents/.tmp/task/pdf-tex-rebuild/$case_name}"

bash "$SCRIPT_DIR/build.sh" "$pdf_path" "$case_name"

for path in \
  "$case_dir/meta/pdfinfo.txt" \
  "$case_dir/raw/layout.txt" \
  "$case_dir/raw/bbox-layout.html" \
  "$case_dir/raw/layout.xml" \
  "$case_dir/parsed/anchors.json" \
  "$case_dir/parsed/refs.json" \
  "$case_dir/parsed/report.md" \
  "$case_dir/rebuild/recovered_stub.tex"
do
  if [[ ! -s "$path" ]]; then
    echo "Expected non-empty output missing: $path" >&2
    exit 1
  fi
done

python3 - "$case_dir/parsed/anchors.json" "$case_dir/parsed/refs.json" <<'PY'
import json
import sys
from pathlib import Path

anchors = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
refs = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

eq_count = anchors["counts"].get("equation", 0)
fig_count = anchors["counts"].get("figure", 0)
table_count = anchors["counts"].get("table", 0)
ref_total = refs["counts"]["total"]

assert eq_count >= 3, f"expected at least 3 equations, got {eq_count}"
assert fig_count >= 1, f"expected at least 1 figure, got {fig_count}"
assert table_count >= 1, f"expected at least 1 table, got {table_count}"
assert ref_total >= 5, f"expected at least 5 references, got {ref_total}"
print(f"anchors: equations={eq_count}, figures={fig_count}, tables={table_count}")
print(f"references: total={ref_total}, unresolved={refs['counts']['unresolved']}")
PY

if command -v pdflatex >/dev/null 2>&1; then
  (
    cd "$case_dir/rebuild"
    pdflatex -interaction=nonstopmode -halt-on-error recovered_stub.tex >/dev/null
  )
fi

echo "Smoke test passed: $case_dir"
