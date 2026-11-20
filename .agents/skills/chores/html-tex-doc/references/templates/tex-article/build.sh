#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p outputs

xelatex -interaction=nonstopmode -halt-on-error -output-directory=outputs main.tex
if grep -Fq '\bibdata' outputs/main.aux 2>/dev/null; then
  BIBINPUTS=".:html/src:${BIBINPUTS:-}" bibtex outputs/main
  xelatex -interaction=nonstopmode -halt-on-error -output-directory=outputs main.tex
fi
xelatex -interaction=nonstopmode -halt-on-error -output-directory=outputs main.tex
