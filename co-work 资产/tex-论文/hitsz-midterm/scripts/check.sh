#!/usr/bin/env bash
# 独立验收入口，不依赖原仓库技能脚本。
set -euo pipefail
template_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$template_dir"
for program in rg pdfinfo; do
  command -v "$program" >/dev/null || { echo "缺少验证程序：$program" >&2; exit 1; }
done
bash build.sh
if rg -n 'begin\{(figure|table)\}\[H\]|^[[:space:]]*\\clearpage[[:space:]]*$' sections midterm-report.tex; then
  echo "请复查强制图表位置或硬换页。" >&2
  exit 3
fi
pdfinfo output/midterm-report.pdf | rg 'Pages:|Page size:|File size:'
echo "构建和基础布局检查通过；提交前仍需人工查看 PDF。"
