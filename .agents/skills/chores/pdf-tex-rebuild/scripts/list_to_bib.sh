#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <tex_with_enumerated_refs> <output_bib>" >&2
  exit 1
fi

tex_path="$1"
output_bib="$2"

python3 - "$tex_path" "$output_bib" <<'PY'
import re
import sys
import unicodedata
from pathlib import Path

tex = Path(sys.argv[1]).read_text(encoding="utf-8")
out = Path(sys.argv[2])

match = re.search(
    r"\\section\*\{参考文献\}\s*\\begin\{enumerate\}\[.*?\](.*?)\\end\{enumerate\}",
    tex,
    re.S,
)
if not match:
  raise SystemExit("Could not locate manual reference enumerate block")

items = re.findall(r"\\item\s+(.*?)(?=(?:\n\\item|\Z))", match.group(1), re.S)
venue_markers = (
    "In ",
    "arXiv",
    "Technical report",
    "International Journal",
    "The Annals of Statistics",
    "AISTATS Proceedings",
    "MIT Press",
    "Charles University",
    "ICLR",
    "ICML",
    "ICCV",
    "NIPS",
)

def slug(text: str) -> str:
  text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
  text = re.sub(r"[^A-Za-z0-9]+", "", text)
  return text.lower()

entries = []
used = set()

for item in items:
  line = " ".join(part.strip() for part in item.splitlines()).strip()
  line = line.replace(r"\&", "&")
  segments = [p.strip().rstrip(".") for p in re.split(r"\.\s+", line) if p.strip()]
  if len(segments) < 2:
    continue
  split_idx = None
  for idx in range(1, len(segments) - 1):
    title_candidate = segments[idx]
    remainder_candidate = ". ".join(segments[idx + 1:])
    if title_candidate.count(",") > 2:
      continue
    if not any(marker in remainder_candidate for marker in venue_markers):
      continue
    split_idx = idx
    break
  if split_idx is None:
    split_idx = 1
  authors = ". ".join(segments[:split_idx]).strip()
  title = segments[split_idx].strip()
  remainder = ". ".join(segments[split_idx + 1:]).strip()
  authors = authors.replace(", and ", " and ")
  authors = authors.replace(", ", " and ")
  year_match = re.search(r"(19|20)\d{2}[a-z]?", line)
  year = year_match.group(0) if year_match else "unknown"
  first_author = authors.split(" and ")[0].split(",")[0].split()[-1]
  first_word = slug(title.split()[0]) if title.split() else "paper"
  key_base = slug(first_author) + year + first_word
  key = key_base
  suffix = 1
  while key in used:
    suffix += 1
    key = f"{key_base}{suffix}"
  used.add(key)

  entry_type = "misc"
  fields = {
      "author": authors,
      "title": title,
      "year": year,
  }
  if "Technical report" in line:
    entry_type = "techreport"
  elif "arXiv preprint" in line or "arXiv:" in line:
    entry_type = "misc"
    arxiv_match = re.search(r"arXiv(?::| preprint arXiv:)([0-9.]+)", line)
    if arxiv_match:
      fields["eprint"] = arxiv_match.group(1)
      fields["archivePrefix"] = "arXiv"
  elif remainder.startswith("In "):
    entry_type = "inproceedings"
    fields["booktitle"] = remainder[3:].rstrip(".")
  elif "Journal" in line or "Annals of Statistics" in line:
    entry_type = "article"
    fields["journal"] = remainder.rstrip(".")
  else:
    fields["note"] = remainder.rstrip(".")

  if entry_type == "misc" and "note" not in fields and remainder:
    fields["note"] = remainder.rstrip(".")

  entries.append((key, entry_type, fields))

def bib_escape(text: str) -> str:
  return text.replace("{", "\\{").replace("}", "\\}")

chunks = []
for key, entry_type, fields in entries:
  chunks.append(f"@{entry_type}{{{key},")
  for field, value in fields.items():
    if not value:
      continue
    chunks.append(f"  {field} = {{{bib_escape(value)}}},")
  chunks.append("}")
  chunks.append("")

out.write_text("\n".join(chunks), encoding="utf-8")
print(out)
PY
