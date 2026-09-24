#!/usr/bin/env bash
# 编译并修复 Evince 文本拖选；输出始终位于源码树外，复用已安装的 PyMuPDF。
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
build_dir="$(realpath -m -- "${1:-$project_dir/../build}")"
[[ "$build_dir" != "$project_dir" && "$build_dir" != "$project_dir/"* && "$project_dir" != "$build_dir/"* ]] || {
  echo '构建目录必须与源码分离' >&2; exit 2;
}
owner="$project_dir/main.tex"
if [[ -d "$build_dir" ]]; then
  [[ -f "$build_dir/.translation-build" && "$(< "$build_dir/.translation-build")" == "$owner" ]] || {
    echo '构建目录不属于本工程' >&2; exit 2;
  }
else
  mkdir -p -- "$build_dir"
  printf '%s\n' "$owner" > "$build_dir/.translation-build"
fi
# 优先显式解释器，其次查找仓库共享环境，最后使用系统 Python。
python_bin="${QTM_PYTHON:-}"
search_dir="$project_dir"
while [[ -z "$python_bin" && "$search_dir" != / ]]; do
  if [[ -x "$search_dir/.agents/sandbox/.venv/bin/python" ]]; then
    python_bin="$search_dir/.agents/sandbox/.venv/bin/python"
  fi
  search_dir="$(dirname -- "$search_dir")"
done
python_bin="${python_bin:-python3}"
"$python_bin" -c 'import pymupdf' || { echo '请通过 QTM_PYTHON 指定已安装 PyMuPDF 的 Python' >&2; exit 3; }
(
  cd -- "$project_dir"
  latexmk -xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error "-outdir=$build_dir" main.tex
) > "$build_dir/build-console.log" 2>&1 || { tail -35 "$build_dir/build-console.log" >&2; exit 1; }
if grep -E '(^!|Overfull|Missing character|undefined|multiply defined)' "$build_dir/main.log"; then
  echo 'TeX 编译门禁未通过' >&2; exit 1
fi
cp -- "$build_dir/main.pdf" "$build_dir/main.raw.pdf"
"$python_bin" "$project_dir/tools/normalize_text_matrices.py" "$build_dir/main.raw.pdf" "$build_dir/main.normalized.pdf"
mv -- "$build_dir/main.normalized.pdf" "$build_dir/main.pdf"
printf '%s\n' "$build_dir/main.pdf"
