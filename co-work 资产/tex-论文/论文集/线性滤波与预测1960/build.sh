#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p outputs

xelatex -interaction=nonstopmode -halt-on-error -output-directory=outputs main.tex
BIBINPUTS=".:html/src:${BIBINPUTS:-}" bibtex outputs/main
xelatex -interaction=nonstopmode -halt-on-error -output-directory=outputs main.tex
xelatex -interaction=nonstopmode -halt-on-error -output-directory=outputs main.tex
