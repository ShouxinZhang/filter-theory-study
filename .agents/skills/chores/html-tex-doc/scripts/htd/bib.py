"""BibTeX 解析与参考文献条目格式化。"""
from __future__ import annotations

import html
import re
import unicodedata

def _clean_bib_val(v: str) -> str:
    v = re.sub(
        r"""\\(["'`^~])\{?(\w)\}?""",
        lambda m: unicodedata.normalize(
            "NFC",
            m.group(2) + {'"': "\u0308", "'": "\u0301", "`": "\u0300", "^": "\u0302", "~": "\u0303"}[m.group(1)],
        ),
        v,
    )
    v = v.replace(r"\&", "&").replace("--", "–").replace("{", "").replace("}", "").replace("~", " ")
    return html.escape(" ".join(v.split()), quote=False)


def parse_bib(text: str) -> dict[str, dict[str, str]]:
    text = re.sub(r"^\s*%.*$", "", text, flags=re.M)
    out: dict[str, dict[str, str]] = {}
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        i, depth = m.end(), 1
        j = i
        while depth and j < len(text):
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        body, fields, pos = text[i : j - 1], {}, 0
        while fm := re.compile(r"\s*,?\s*(\w+)\s*=\s*").match(body, pos):
            k = fm.end()
            if body[k : k + 1] == "{":
                d, e = 1, k + 1
                while d and e < len(body):
                    d += {"{": 1, "}": -1}.get(body[e], 0)
                    e += 1
                val = body[k + 1 : e - 1]
            elif body[k : k + 1] == '"':
                e = body.index('"', k + 1) + 1
                val = body[k + 1 : e - 1]
            else:
                e = body.find(",", k)
                e = len(body) if e < 0 else e
                val = body[k:e]
            fields[fm.group(1).lower()] = val
            pos = e
        out[m.group(2)] = fields
    return out


def fmt_ref(f: dict[str, str]) -> str:
    names = []
    for a in re.split(r"\s+and\s+", f.get("author", "")):
        if "," in a and not a.strip().startswith("{"):
            last, first = a.split(",", 1)
            a = f"{first.strip()} {last.strip()}"
        if a.strip():
            names.append(_clean_bib_val(a))
    who = ", ".join(names[:3]) + (" et al." if len(names) > 3 else "")
    venue = next((f[k] for k in ("journal", "booktitle", "publisher", "school", "howpublished") if f.get(k)), "")
    bits = [
        who,
        _clean_bib_val(f.get("title", "")),
        f"<em>{_clean_bib_val(venue)}</em>" if venue else "",
        _clean_bib_val(f.get("year", "")),
    ]
    return ". ".join(b for b in bits if b) + "."
