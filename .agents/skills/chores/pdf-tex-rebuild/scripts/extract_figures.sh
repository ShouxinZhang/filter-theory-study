#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <case_dir> <source_pdf> <output_figure_dir>" >&2
  exit 1
fi

case_dir="$1"
source_pdf="$2"
figure_dir="$3"
layout_xml="$case_dir/raw/layout.xml"

for tool in pdftocairo convert identify python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing required tool: $tool" >&2
    exit 1
  fi
done

if [[ ! -f "$layout_xml" ]]; then
  echo "Missing layout xml: $layout_xml" >&2
  exit 1
fi

mkdir -p "$figure_dir"

tmpdir="$(mktemp -d)"
cleanup() {
  rm -rf "$tmpdir"
}
trap cleanup EXIT

plan_json="$tmpdir/crop-plan.json"

python3 - "$layout_xml" "$plan_json" <<'PY'
import json
import re
import xml.etree.ElementTree as ET
import sys
from pathlib import Path

layout_xml = Path(sys.argv[1])
plan_json = Path(sys.argv[2])
root = ET.parse(layout_xml).getroot()

plan = []
for page_idx, page in enumerate(root.findall("page"), start=1):
    width = int(page.attrib["width"])
    height = int(page.attrib["height"])
    texts = []
    for node in page.findall("text"):
      text = "".join(node.itertext()).strip().replace("\n", " ")
      if text:
        texts.append({
          "top": int(node.attrib["top"]),
          "left": int(node.attrib["left"]),
          "text": text,
        })
    texts.sort(key=lambda x: (x["top"], x["left"]))
    figure_caps = [t for t in texts if re.match(r"^Figure\s+\d+:", t["text"])]
    anchors = [t for t in texts if t["text"].startswith(("Figure ", "Table "))]
    by_top = {}
    for cap in figure_caps:
      by_top.setdefault(cap["top"], []).append(cap)
    for cap in figure_caps:
      number = cap["text"].split(":", 1)[0].split()[1]
      shared = sorted(by_top[cap["top"]], key=lambda x: x["left"])
      prev_anchor_tops = [a["top"] for a in anchors if a["top"] < cap["top"]]
      if prev_anchor_tops:
        crop_top = max(prev_anchor_tops) + 42
      else:
        previous_text_tops = [t["top"] for t in texts if t["top"] < cap["top"] - 60]
        crop_top = max(previous_text_tops) + 28 if previous_text_tops else 120
      crop_bottom = cap["top"] - 18
      crop_top = max(120, crop_top)
      if crop_bottom - crop_top < 120:
        crop_top = max(120, crop_bottom - 260)
      if len(shared) > 1:
        idx = shared.index(cap)
        midpoint = width // 2
        if idx == 0:
          crop_left = 40
          crop_right = midpoint - 18
        else:
          crop_left = midpoint + 18
          crop_right = width - 40
      else:
        crop_left = 40
        crop_right = width - 40
      plan.append({
        "figure_no": number,
        "page": page_idx,
        "page_width": width,
        "page_height": height,
        "crop_left": crop_left,
        "crop_top": crop_top,
        "crop_right": crop_right,
        "crop_bottom": crop_bottom,
      })

plan_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

pages="$(python3 - "$plan_json" <<'PY'
import json, sys
from pathlib import Path
plan = json.loads(Path(sys.argv[1]).read_text())
print(" ".join(str(x) for x in sorted({item["page"] for item in plan})))
PY
)"

for page in $pages; do
  pdftocairo -png -singlefile -f "$page" -l "$page" "$source_pdf" "$tmpdir/page-$page" >/dev/null 2>&1
done

python3 - "$plan_json" "$tmpdir" "$figure_dir" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

plan = json.loads(Path(sys.argv[1]).read_text())
tmpdir = Path(sys.argv[2])
figure_dir = Path(sys.argv[3])
figure_dir.mkdir(parents=True, exist_ok=True)

for item in plan:
  page_png = tmpdir / f"page-{item['page']}.png"
  identify = subprocess.check_output(
      ["identify", "-format", "%w %h", str(page_png)],
      text=True,
  ).strip()
  img_w, img_h = map(int, identify.split())
  scale_x = img_w / item["page_width"]
  scale_y = img_h / item["page_height"]
  left = max(0, round(item["crop_left"] * scale_x))
  top = max(0, round(item["crop_top"] * scale_y))
  right = min(img_w, round(item["crop_right"] * scale_x))
  bottom = min(img_h, round(item["crop_bottom"] * scale_y))
  width = max(10, right - left)
  height = max(10, bottom - top)
  out = figure_dir / f"fig{item['figure_no']}.png"
  subprocess.run(
      [
          "convert",
          str(page_png),
          "-crop",
          f"{width}x{height}+{left}+{top}",
          "+repage",
          str(out),
      ],
      check=True,
  )
  print(out)
PY
