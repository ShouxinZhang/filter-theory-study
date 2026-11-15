#!/usr/bin/env python3
"""薄适配器参考实现：将 hithesis 风格 TeX 章节单向导入为 html-tex-doc 受控 Markdown。"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEX = HERE / "tex_demo"
SRC = HERE / "src"
THM = {"theorem": "定理", "proposition": "命题", "lemma": "引理", "definition": "定义"}
KIND = "算法|式|图|表|命题|定理|引理|定义"


def convert_chapter(raw: str) -> str:
    s = re.sub(r"^[ \t]*%.*\n", "", raw, flags=re.M)
    s = re.sub(r"\\ifhit@openright.*?\\fi", "", s)
    stash: list[str] = []

    def keep(block: str) -> str:
        stash.append(block)
        return f"\n\n@@S{len(stash) - 1}@@\n\n"

    def on_alg(m: re.Match[str]) -> str:
        body = m.group(1)
        cap_m = re.search(r"\\caption\{([^}]*)\}", body)
        lab_m = re.search(r"\\label\{([^}]*)\}", body)
        cap = cap_m.group(1) if cap_m else ""
        lab = lab_m.group(1) if lab_m else "alg:auto"
        name = lab.split(":")[-1]
        body = re.sub(r"\\(caption|label)\{[^}]*\}", "", body).strip()
        body = re.sub(r"(%s)~?\\(?:eq)?ref\{([^}]+)\}" % KIND, r"\\cref{\2}", body)
        body = re.sub(r"\\(?:eq)?ref\{([^}]+)\}", r"\\cref{\1}", body)
        (SRC / "algs").mkdir(parents=True, exist_ok=True)
        (SRC / "algs" / f"{name}.tex").write_text(
            "\\documentclass[varwidth=15.5cm,border=1pt]{standalone}\n"
            "\\input{common}\n\\input{alg2e}\n\\begin{document}\n"
            f"\\begin{{algorithm}}[H]\n{body}\n\\end{{algorithm}}\n\\end{{document}}\n",
            encoding="utf-8",
        )
        return keep(
            f'<figure class="alg" data-label="{lab}" data-tex="algs/{name}.tex">\n'
            f"<figcaption>{cap}</figcaption>\n<!--TEX-->\n</figure>"
        )

    def on_eq(m: re.Match[str]) -> str:
        body = m.group(1)
        lab_m = re.search(r"\\label\{([^}]+)\}", body)
        body = re.sub(r"\\label\{[^}]+\}", "", body).strip()
        attr = f" {{#{lab_m.group(1)}}}" if lab_m else ""
        return keep(f"$${attr}\n{body}\n$$")

    s = re.sub(r"\\begin\{algorithm\}(?:\[[^\]]*\])?(.*?)\\end\{algorithm\}", on_alg, s, flags=re.S)
    s = re.sub(r"\\begin\{equation\}(.*?)\\end\{equation\}", on_eq, s, flags=re.S)
    s = re.sub(
        r"\\begin\{(%s)\}(?:\[(.*?)\])?\s*(?:\\label\{([^}]+)\})?" % "|".join(THM),
        lambda m: f"\n\n::: {THM[m.group(1)]}" + (f" {{#{m.group(3)}}}" if m.group(3) else "") + (f" {m.group(2)}" if m.group(2) else "") + "\n\n",
        s,
    )
    s = re.sub(r"\\begin\{proof\}", "\n\n::: 证明\n\n", s)
    s = re.sub(r"\\end\{(%s|proof)\}" % "|".join(THM), "\n\n:::\n\n", s)
    for cmd, h in (("chapter", "#"), ("section", "##"), ("subsection", "###")):
        s = re.sub(
            rf"\\{cmd}\{{([^}}]+)\}}(?:\\label\{{([^}}]+)\}})?",
            lambda m, hh=h: f"\n\n{hh} {m.group(1)}" + (f" {{#{m.group(2)}}}" if m.group(2) else "") + "\n\n",
            s,
        )
    s = re.sub(r"(%s)~?\\(?:eq)?ref\{([^}]+)\}" % KIND, r"{@\2}", s)
    s = re.sub(r"\\eqref\{([^}]+)\}", r"({@\1|n})", s)
    s = re.sub(r"\\ref\{([^}]+)\}", r"{@\1|n}", s)
    s = re.sub(r"~?\\cite\{([^}]+)\}", lambda m: "[@" + re.sub(r"\s+", "", m.group(1)) + "]", s)
    s = s.replace("~", " ")
    s = re.sub(r"@@S(\d+)@@", lambda m: stash[int(m.group(1))], s)
    return re.sub(r"\n{3,}", "\n\n", s).strip() + "\n"


def main() -> int:
    SRC.mkdir(parents=True, exist_ok=True)
    (SRC / "00_摘要.md").write_text(
        "<!-- title: hithesis 薄适配器示例：粒子流非线性滤波 -->\n\n"
        '<header class="title">\n<h1>hithesis 薄适配器示例：粒子流非线性滤波</h1>\n'
        '<p class="subtitle">薄适配器导出演示 · 受控 Markdown + algorithm2e 矢量内联</p>\n'
        "</header>\n\n<!--TOC-->\n\n"
        '<p class="h2">摘要</p>\n\n'
        "本文演示如何通过项目侧轻量脚本将 `hithesis` 章节转换为通用 `html-tex-doc` 受控 Markdown。\n",
        encoding="utf-8",
    )
    (SRC / "01_状态估计基础.md").write_text(
        convert_chapter((TEX / "chapter01.tex").read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    (SRC / "99_参考文献.md").write_text("# 参考文献\n\n<!--REFS-->\n", encoding="utf-8")
    shutil.copy(TEX / "refs.bib", SRC / "refs.bib")
    print(f"已导入至 {SRC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
