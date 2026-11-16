#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <case_dir>" >&2
  exit 1
fi

case_dir="$1"
layout_txt="$case_dir/raw/layout.txt"
source_pdf_file="$case_dir/meta/source_pdf.txt"

if [[ ! -f "$layout_txt" ]]; then
  echo "Missing layout text: $layout_txt" >&2
  exit 1
fi

python3 - "$layout_txt" "$source_pdf_file" "$case_dir/parsed/anchors.json" "$case_dir/parsed/refs.json" "$case_dir/parsed/report.md" <<'PY'
import json
import re
import sys
from pathlib import Path

layout_path = Path(sys.argv[1])
source_pdf = Path(sys.argv[2]).read_text(encoding="utf-8").strip()
anchors_path = Path(sys.argv[3])
refs_path = Path(sys.argv[4])
report_path = Path(sys.argv[5])

raw_text = layout_path.read_text(encoding="utf-8", errors="replace")
pages = raw_text.split("\f")

equation_line_re = re.compile(r"^(?P<body>.+?)\s+\((?P<num>\d+)\)\s*$")
explicit_ref_patterns = [
    ("equation", re.compile(r"\bEquation\s+(\d+)\b"), "Equation {num}", "high"),
    ("equation", re.compile(r"\bEq\.?\s*\(?(\d+)\)?"), "Eq. {num}", "high"),
    ("figure", re.compile(r"\bFigure\s+(\d+)\b"), "Figure {num}", "high"),
    ("figure", re.compile(r"\bFig\.?\s+(\d+)\b"), "Fig. {num}", "high"),
    ("table", re.compile(r"\bTable\s+(\d+)\b"), "Table {num}", "high"),
    ("algorithm", re.compile(r"\bAlgorithm\s+(\d+)\b"), "Algorithm {num}", "high"),
]
caption_token_re = re.compile(r"(Figure|Fig\.|Table|Algorithm)\s+(\d+)\s*:\s*")
bare_parenthesized_re = re.compile(r"(?<![A-Za-z0-9])\((\d{1,3})\)")
algorithm_anchor_re = re.compile(r"^Algorithm\s+(\d+)\s+(.+)$")

def looks_like_equation(text: str) -> bool:
    signals = ["=", "<", ">", "+", "-", "/", "^", " inf ", " sup ", "Tr[", "Tr ", " E[", " E(", " k ", "||"]
    padded = f" {text} "
    return any(signal in padded for signal in signals)

anchors = []
refs = []
anchor_lookup = {}

def add_anchor(kind: str, number: str, page: int, line_number: int, text: str, confidence: str) -> None:
    label_prefix = {
        "equation": "eq",
        "figure": "fig",
        "table": "tbl",
        "algorithm": "alg",
    }[kind]
    label = f"{label_prefix}:auto-{number}"
    entry = {
        "kind": kind,
        "number": number,
        "label": label,
        "page": page,
        "line_number": line_number,
        "confidence": confidence,
        "text": text.strip(),
    }
    key = (kind, number)
    if key not in anchor_lookup:
        anchor_lookup[key] = label
        anchors.append(entry)

for page_index, page_text in enumerate(pages, start=1):
    page_lines = page_text.splitlines()
    for line_index, raw_line in enumerate(page_lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        caption_matches = list(caption_token_re.finditer(line))
        if caption_matches:
            for idx, match in enumerate(caption_matches):
                start = match.start()
                end = caption_matches[idx + 1].start() if idx + 1 < len(caption_matches) else len(line)
                chunk = line[start:end].strip()
                kind_token, number = match.group(1), match.group(2)
                kind = {
                    "Figure": "figure",
                    "Fig.": "figure",
                    "Table": "table",
                    "Algorithm": "algorithm",
                }[kind_token]
                add_anchor(kind, number, page_index, line_index, chunk, "high")
            continue

        algorithm_anchor_match = algorithm_anchor_re.match(line)
        if algorithm_anchor_match:
            add_anchor("algorithm", algorithm_anchor_match.group(1), page_index, line_index, line, "medium")
            continue

        eq_match = equation_line_re.match(line)
        if eq_match and looks_like_equation(eq_match.group("body")):
            add_anchor("equation", eq_match.group("num"), page_index, line_index, line, "medium")
            continue

for page_index, page_text in enumerate(pages, start=1):
    page_lines = page_text.splitlines()
    for line_index, raw_line in enumerate(page_lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        is_anchor_line = any(
            anchor["page"] == page_index and anchor["line_number"] == line_index
            for anchor in anchors
        )

        seen = set()
        for kind, pattern, pattern_name, confidence in explicit_ref_patterns:
            for match in pattern.finditer(line):
                number = match.group(1)
                key = (kind, number, pattern_name)
                if key in seen:
                    continue
                seen.add(key)
                refs.append({
                    "kind": kind,
                    "number": number,
                    "target_label": anchor_lookup.get((kind, number)),
                    "pattern": pattern_name.format(num=number),
                    "confidence": confidence,
                    "page": page_index,
                    "line_number": line_index,
                    "text": line,
                })

        if not is_anchor_line:
            for match in bare_parenthesized_re.finditer(line):
                number = match.group(1)
                key = ("equation", number, "bare-parenthesized-number")
                if key in seen:
                    continue
                if ("equation", number) not in anchor_lookup:
                    continue
                seen.add(key)
                refs.append({
                    "kind": "equation",
                    "number": number,
                    "target_label": anchor_lookup.get(("equation", number)),
                    "pattern": "bare-parenthesized-number",
                    "confidence": "low",
                    "page": page_index,
                    "line_number": line_index,
                    "text": line,
                })

anchors.sort(key=lambda item: (item["kind"], int(item["number"]), item["page"], item["line_number"]))
refs.sort(key=lambda item: (item["page"], item["line_number"], item["kind"], int(item["number"])))

anchor_counts = {}
for anchor in anchors:
    anchor_counts[anchor["kind"]] = anchor_counts.get(anchor["kind"], 0) + 1

resolved = sum(1 for item in refs if item["target_label"])
unresolved = len(refs) - resolved

anchors_payload = {
    "source_pdf": source_pdf,
    "counts": anchor_counts,
    "anchors": anchors,
}
refs_payload = {
    "counts": {
        "total": len(refs),
        "resolved": resolved,
        "unresolved": unresolved,
    },
    "references": refs,
}

anchors_path.write_text(json.dumps(anchors_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
refs_path.write_text(json.dumps(refs_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

low_conf_refs = [item for item in refs if item["confidence"] == "low"]
unresolved_refs = [item for item in refs if item["target_label"] is None]

report_lines = [
    "# Parse Report",
    "",
    f"- source_pdf: `{source_pdf}`",
    f"- anchor_counts: `{json.dumps(anchor_counts, ensure_ascii=False)}`",
    f"- ref_total: `{len(refs)}`",
    f"- ref_resolved: `{resolved}`",
    f"- ref_unresolved: `{unresolved}`",
    "",
    "## Review Queue",
    "",
]

if low_conf_refs:
    report_lines.append("### Low Confidence Equation References")
    report_lines.append("")
    for item in low_conf_refs[:20]:
        report_lines.append(
            f"- page {item['page']} line {item['line_number']}: `{item['pattern']}` -> `{item['target_label']}`"
        )
    report_lines.append("")

if unresolved_refs:
    report_lines.append("### Unresolved References")
    report_lines.append("")
    for item in unresolved_refs[:20]:
        report_lines.append(
            f"- page {item['page']} line {item['line_number']}: `{item['kind']} {item['number']}` in `{item['text']}`"
        )
    report_lines.append("")

if not low_conf_refs and not unresolved_refs:
    report_lines.append("- No low-confidence or unresolved references in the current pass.")
    report_lines.append("")

report_path.write_text("\n".join(report_lines), encoding="utf-8")
print(f"Wrote {anchors_path}")
print(f"Wrote {refs_path}")
print(f"Wrote {report_path}")
PY
