"""标签扫描、统一编号与 labels.tex 生成。"""
from __future__ import annotations

import html
import re
from pathlib import Path

FORMATS = {"sec": "第 {n} 节", "eq": "式 ({n})", "fig": "图 {n}", "alg": "算法 {n}", "tbl": "表 {n}"}


OPEN_TAG = re.compile(r"<(h2|h3|div|figure)\b([^>]*)>")


ATTR = re.compile(r'([\w-]+)="([^"]*)"')


REF = re.compile(r"\{@([\w:.-]+)(\|n)?\}")


def attrs(s: str) -> dict[str, str]:
    return dict(ATTR.findall(s))


def _keep_loc(a: dict[str, str], include_tex: bool = False) -> str:
    keys = ["data-file", "data-l", "data-l1", "data-l2"]
    if include_tex:
        keys.append("data-tex")
    parts = [f'{k}="{html.escape(a[k], quote=True)}"' for k in keys if k in a]
    return (" " + " ".join(parts)) if parts else ""


def anchor(key: str) -> str:
    return re.sub(r"[^\w-]", "-", key)


def classify(tag: str, a: dict[str, str]) -> str | None:
    cls = a.get("class", "")
    if tag in ("h2", "h3"):
        return "sec"
    if tag == "div" and "eq" in cls.split():
        return "eq" if "data-label" in a else None
    if tag == "div" and cls == "thm":
        return "thm"
    if tag == "figure" and cls in ("fig", "alg", "tbl"):
        return cls
    return None


def auto_label_sections(doc: str) -> str:
    count = 0

    def fn(m: re.Match[str]) -> str:
        nonlocal count
        if m.group(1) in ("h2", "h3") and "data-label" not in m.group(2):
            count += 1
            return f'<{m.group(1)}{m.group(2)} data-label="sec:auto-{count}">'
        return m.group(0)

    return OPEN_TAG.sub(fn, doc)


def number(doc: str, errors: list[str]) -> dict[str, dict[str, str]]:
    labels: dict[str, dict[str, str]] = {}
    sec = [0, 0]
    counters: dict[str, int] = {}
    for m in OPEN_TAG.finditer(doc):
        tag, a = m.group(1), attrs(m.group(2))
        kind = classify(tag, a)
        if not kind:
            continue
        key = a.get("data-label")
        if not key:
            errors.append(f"缺少 data-label：{m.group(0)}")
            continue
        if kind == "sec":
            if tag == "h2":
                sec = [sec[0] + 1, 0]
                num = str(sec[0])
            else:
                sec[1] += 1
                num = f"{sec[0]}.{sec[1]}"
            text = FORMATS["sec"].format(n=num)
        elif kind == "thm":
            k = a.get("data-kind", "定理")
            counters[k] = counters.get(k, 0) + 1
            num = str(counters[k])
            text = f"{k} {num}"
        else:
            counters[kind] = counters.get(kind, 0) + 1
            num = str(counters[kind])
            text = FORMATS[kind].format(n=num)
        if key in labels:
            errors.append(f"重复标签：{key}")
        labels[key] = {"kind": kind, "num": num, "id": anchor(key), "text": text}
    return labels


def write_labels_tex(labels: dict[str, dict[str, str]], build_dir: Path) -> Path:
    path = build_dir / "labels.tex"
    lines = ["% 由 html_tex_doc.py 生成，勿手改。\\lbl{key}{显示文本}{HTML id}"]
    lines += [f"\\lbl{{{k}}}{{{v['text'].replace(' ', '~')}}}{{{v['id']}}}" for k, v in labels.items()]
    new = "\n".join(lines) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != new:
        path.write_text(new, encoding="utf-8")
    return path
