#!/usr/bin/env bash
# 从任意工作目录构建，所有路径均加引号以支持中文和空格。
set -euo pipefail
template_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$template_dir"
report_main=main
for program in xelatex bibtex; do
  command -v "$program" >/dev/null || { echo "缺少编译程序：$program" >&2; exit 1; }
done
mkdir -p build output
# BibTeX 从模板根查找引用库和本地 BST，输出仍留在 build 中。
export BIBINPUTS="$template_dir:${BIBINPUTS-}"
export BSTINPUTS="$template_dir:${BSTINPUTS-}"
compile_tex() {
  xelatex -halt-on-error -synctex=1 -interaction=nonstopmode \
    -file-line-error -output-directory=build "$report_main.tex"
}
compile_tex
if grep -q '^\\citation' "build/$report_main.aux"; then
  bibtex "build/$report_main"
else
  # 无引用时清空旧的生成 BBL，避免残留上次参考文献。
  : > "build/$report_main.bbl"
fi
compile_tex
compile_tex
# 不发布存在未解析交叉引用或溢出的输出。
if grep -En 'undefined|Overfull|Missing character:|Fatal|Emergency stop|! LaTeX Error' "build/$report_main.log"; then
  echo "发现未解析引用、溢出或编译错误，请检查 build 日志。" >&2
  exit 2
fi
cp "build/$report_main.pdf" "output/$report_main.pdf"
echo "编译完成：$template_dir/output/$report_main.pdf"
