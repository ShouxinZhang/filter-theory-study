#!/usr/bin/env python3
"""一次性导入：把上级目录的 TeX 论文转成 src/ 下的 Markdown 独立副本。

警告：会覆盖 src/ 中的同名 .md、algs/*.tex、figs/*.svg 与 refs.bib；导入后两边不再同步。
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = HERE / "src"
SKILL = next(p for p in HERE.parents if (p / ".agents/skills/chores/html-tex-doc").exists()) / ".agents/skills/chores/html-tex-doc"

H2 = '<p class="h2">%s</p>'  # 摘要不参与章节编号
KIND = "算法|式|图|表|命题|定理|引理|假设|定义|推论"
THM = {"theorem": "定理", "proposition": "命题", "lemma": "引理", "definition": "定义",
       "assumption": "假设", "corollary": "推论", "remark": "注"}
FILES = [
    ("01_绪论", ["body/chapter01"]),
    ("02_理论基础", ["body/chapter02"]),
    ("03_算法分析", ["sections/completed_work/05_algorithms"]),
    ("04_数值仿真", ["sections/completed_work/06_simulation"]),
    ("05_结论", ["back/conclusion"]),
    ("06_AI使用声明", ["back/ai_statement"]),
    ("08_附录A_Bayes", ["back/appendix_bayes"]),
    ("09_附录B_Monge", ["back/appendix_monge"]),
    ("10_附录C_流形", ["back/appendix_manifold"]),
    ("11_成果与致谢", ["back/publications", "back/acknowledgements"]),
]


def read(rel: str) -> str:
    p = ROOT / rel
    if p.suffix != ".tex":
        p = p.with_name(p.name + ".tex")
    t = p.read_text(encoding="utf-8")
    t = re.sub(r"^[ \t]*%.*\n", "", t, flags=re.M)
    t = re.sub(r"(?<!\\)%.*", "", t)
    return re.sub(r"\\input\{([^}]+)\}", lambda m: read(m.group(1)), t)


def grab(s: str, i: int) -> tuple[str, int]:
    d = 0
    for j in range(i, len(s)):
        if s[j] == "{" and s[j - 1:j] != "\\":
            d += 1
        elif s[j] == "}" and s[j - 1:j] != "\\":
            d -= 1
            if d == 0:
                return s[i + 1:j], j + 1
    raise ValueError("花括号不配对：" + s[i:i + 60])


def sub_cmd(s: str, name: str, nargs: int, fn) -> str:
    out, i, pat = [], 0, re.compile(r"\\" + name + r"(?![a-zA-Z])\*?(\[[^\]]*\])?")
    while m := pat.search(s, i):
        out.append(s[i:m.start()])
        j, args = m.end(), []
        for _ in range(nargs):
            while s[j] in " \n":
                j += 1
            a, j = grab(s, j)
            args.append(a)
        out.append(fn(*args))
        i = j
    out.append(s[i:])
    return "".join(out)


def text(p: str) -> str:
    p = re.sub(r"(%s)~?\\(?:eq)?ref\{([^}]+)\}" % KIND, r"{@\2}", p)
    p = re.sub(r"\\eqref\{([^}]+)\}", r"({@\1|n})", p)
    p = re.sub(r"\\ref\{([^}]+)\}", r"{@\1|n}", p)
    p = re.sub(r"\\cite\{([^}]+)\}", lambda m: "[@%s]" % re.sub(r"\s+", "", m.group(1)), p)
    p = sub_cmd(p, "url", 1, lambda a: f'<a href="{a}">{a}</a>')
    p = re.sub(r"\\(enspace|quad|qquad)(?![a-zA-Z])", " ", p)
    return p.replace("~", " ").replace(r"\%", "%").replace(r"\&", "&amp;").replace("--", "–")


def inline(s: str) -> str:
    s = sub_cmd(s, "textbf", 1, lambda a: f"**{a}**")
    parts = re.split(r"((?<!\\)\$.*?(?<!\\)\$)", s, flags=re.S)
    return "".join(text(p) if i % 2 == 0 else p for i, p in enumerate(parts))


def notes(body: str) -> list[str]:
    """浮动体里除图、表、题注之外的残余文字（“注：……”等）。"""
    for cmd, n in [("caption", 1), ("label", 1), ("vspace", 1), ("setlength", 2), ("hspace", 1), ("includegraphics", 1)]:
        body = sub_cmd(body, cmd, n, lambda *a: "")
    body = re.sub(r"\\parbox\{[^}]*\}|\\sbox0|\\usebox0|\\(centering|par|wuhao|raggedright)(?![a-zA-Z])", "", body)
    out = []
    for line in body.split("\n"):
        line = line.strip()
        while line.startswith("{") and line.endswith("}"):
            line = line[1:-1].strip()
        if line.strip("{} "):
            out.append(f'<p class="note">{inline(line)}</p>')
    return out


def cap_label(body: str) -> tuple[str, str]:
    i = body.find(r"\caption{")
    cap = grab(body, i + 8)[0] if i >= 0 else ""
    lab = re.search(r"\\label\{([^}]+)\}", body)
    return inline(cap), lab.group(1) if lab else ""


def table_html(tab: str) -> str:
    tab = re.sub(r"\\(toprule|bottomrule|hline)(\[[^\]]*\])?", "", tab)
    tab = re.sub(r"\\cmidrule(\([^)]*\))?\{[^}]*\}", "", tab)
    head, _, rest = re.sub(r"\\midrule(\[[^\]]*\])?", "@@MID@@", tab).partition("@@MID@@")
    if not rest:
        head, rest = "", head

    def rows(part: str, tag: str) -> str:
        out = []
        for row in re.split(r"\\\\(?:\[[^\]]*\])?", part):
            if not row.strip():
                continue
            cells = []
            for c in re.split(r"(?<!\\)&", row):
                c, span = c.strip(), ""
                if m := re.match(r"\\multicolumn\{(\d+)\}\{[^}]*\}\{(.*)\}$", c, re.S):
                    span, c = f' colspan="{m.group(1)}"', m.group(2)
                cells.append(f"<{tag}{span}>{inline(c)}</{tag}>")
            out.append("<tr>" + "".join(cells) + "</tr>")
        return "\n".join(out)

    return "<table>\n<thead>\n" + rows(head, "th") + "\n</thead>\n<tbody>\n" + rows(rest, "td") + "\n</tbody>\n</table>"


class Importer:
    def __init__(self) -> None:
        self.stash: list[str] = []
        self.figs: set[str] = set()

    def keep(self, block: str, own_para: bool) -> str:
        self.stash.append(block)
        mark = f"@@S{len(self.stash) - 1}@@"
        return f"\n\n{mark}\n\n" if own_para else f"\n{mark}\n"

    def figure(self, m: re.Match[str]) -> str:
        body = m.group(1)
        cap, lab = cap_label(body)
        imgs = []
        for path in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", body):
            self.figs.add(path)
            imgs.append(f'<img src="figs/{Path(path).stem}.svg" alt="">')
        return self.keep("\n".join([f'<figure class="fig" data-label="{lab}">', *imgs,
                                    f"<figcaption>{cap}</figcaption>", *notes(body), "</figure>"]), True)

    def table(self, m: re.Match[str]) -> str:
        body = m.group(1)
        cap, lab = cap_label(body)
        body = re.sub(r"\\begin\{tabular\}\[c\]\{@\{\}[lcr]@\{\}\}(.*?)\\end\{tabular\}",
                      lambda n: "<br>".join(x.strip() for x in n.group(1).split(r"\\")), body, flags=re.S)
        tab = re.search(r"\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}", body, re.S)
        rest = body[:tab.start()] + body[tab.end():]
        return self.keep("\n".join([f'<figure class="tbl" data-label="{lab}">', f"<figcaption>{cap}</figcaption>",
                                    table_html(tab.group(1)), *notes(rest), "</figure>"]), True)

    def algorithm(self, m: re.Match[str]) -> str:
        body = m.group(1)
        cap, lab = cap_label(body)
        name = lab.split(":")[-1]
        body = sub_cmd(sub_cmd(body, "caption", 1, lambda a: ""), "label", 1, lambda a: "")
        body = re.sub(r"(%s)~?\\(?:eq)?ref\{([^}]+)\}" % KIND, r"\\cref{\2}", body)
        body = re.sub(r"\\(?:eq)?ref\{", r"\\cref{", body)
        (SRC / "algs").mkdir(parents=True, exist_ok=True)
        (SRC / "algs" / f"{name}.tex").write_text(
            "\\documentclass[varwidth=15.5cm,border=1pt]{standalone}\n\\input{common}\n\\input{alg2e}\n"
            "\\begin{document}\n\\begin{algorithm}[H]\n" + body.strip() + "\n\\end{algorithm}\n\\end{document}\n",
            encoding="utf-8")
        return self.keep(f'<figure class="alg" data-label="{lab}" data-tex="algs/{name}.tex">\n'
                         f"<figcaption>{cap}</figcaption>\n<!--TEX-->\n</figure>", True)

    def equation(self, m: re.Match[str]) -> str:
        body = m.group(2)
        lab = re.search(r"\\label\{([^}]+)\}", body)
        body = re.sub(r"\\label\{[^}]+\}", "", body).strip()
        return self.keep("$$" + (f" {{#{lab.group(1)}}}" if lab else "") + f"\n{body}\n$$", False)

    def heading(self, s: str, cmd: str, hashes: str) -> str:
        out, i, pat = [], 0, re.compile(r"\\" + cmd + r"\*?(?=\{)")
        while m := pat.search(s, i):
            out.append(s[i:m.start()])
            title, j = grab(s, m.end())
            if n := re.compile(r"\[[^\]]*\]").match(s, j):
                j = n.end()
            lab = ""
            if n := re.compile(r"\s*\\label\{([^}]+)\}").match(s, j):
                lab, j = f" {{#{n.group(1)}}}", n.end()
            out.append(f"\n\n{hashes} {title}{lab}\n\n")
            i = j
        out.append(s[i:])
        return "".join(out)

    def convert(self, s: str) -> str:
        self.stash = []
        s = re.sub(r"\\makeatletter|\\makeatother|\\ifhit@openright.*?\\fi", "", s)
        s = s.replace(r"\hit@appendix@chapter*", r"\chapter")
        for env, fn in [("figure", self.figure), ("table", self.table), ("algorithm", self.algorithm)]:
            s = re.sub(r"\\begin\{%s\}(?:\[[^\]]*\])?(.*?)\\end\{%s\}" % (env, env), fn, s, flags=re.S)
        s = re.sub(r"\\begin\{(equation\*?)\}(.*?)\\end\{\1\}", self.equation, s, flags=re.S)

        def thm_open(m: re.Match[str]) -> str:
            lab = f" {{#{m.group(4)}}}" if m.group(4) else ""
            return f"\n\n::: {THM[m.group(1)]}{lab} {m.group(2) or ''}".rstrip() + "\n\n"

        s = re.sub(r"\\begin\{(%s)\}(?:\[(.*?)\])?\s*(\\label\{([^}]+)\})?" % "|".join(THM), thm_open, s)
        s = re.sub(r"\\begin\{proof\}(?:\[(.*?)\])?", lambda m: f"\n\n::: 证明 {m.group(1) or ''}".rstrip() + "\n\n", s)
        s = re.sub(r"\\end\{(%s|proof)\}" % "|".join(THM), "\n\n:::\n\n", s)

        for cmd, h in [("chapter", "#"), ("section", "##"), ("subsection", "###")]:
            s = self.heading(s, cmd, h)
        for env, title in [("conclusions", "结论"), ("acknowledgements", "致谢"), ("cabstract", "摘要"),
                           ("eabstract", "Abstract"), ("publication", "攻读硕士学位期间取得创新性成果")]:
            s = s.replace(r"\begin{%s}" % env, f"\n\n# {title}\n\n").replace(r"\end{%s}" % env, "\n\n")

        def lst(m: re.Match[str]) -> str:
            items = [x.strip() for x in re.split(r"\\item(?![a-zA-Z])", m.group(2))[1:]]
            if any("@@S" in x for x in items):
                print("  注意：列表项内含行间公式/浮动体，请人工检查：", items[0][:30], file=sys.stderr)
            bullet = (lambda k: "- ") if m.group(1) == "itemize" else (lambda k: f"{k + 1}. ")
            return "\n\n" + "\n".join(bullet(k) + re.sub(r"\s*\n\s*", "\n", x) for k, x in enumerate(items)) + "\n\n"

        s = re.sub(r"\\begin\{(enumerate|itemize|publist)\}(?:\[[^\]]*\])?(.*?)\\end\{\1\}", lst, s, flags=re.S)
        for cmd, n in [("Needspace", 1), ("vspace", 1)]:
            s = sub_cmd(s, cmd, n, lambda *a: "")
        s = re.sub(r"\\suppressfloats(\[[^\]]*\])?|\\(FloatBarrier|noindent|par|centering)(?![a-zA-Z])", "", s)
        s = inline(s)
        s = re.sub(r"@@S(\d+)@@", lambda m: self.stash[int(m.group(1))], s)
        s = "\n".join(l.strip() for l in s.split("\n"))
        return re.sub(r"\n{3,}", "\n\n", s).strip() + "\n"


def main() -> int:
    for f in ("common.tex", "macros.tex", "style.css"):
        shutil.copy(SKILL / "references/templates/src" / f, SRC / f) if not (SRC / f).exists() else None
    imp = Importer()
    for name, rels in FILES:
        (SRC / f"{name}.md").write_text("\n".join(imp.convert(read(r)) for r in rels), encoding="utf-8")
        print("写入", f"{name}.md")

    cover = (ROOT / "config/cover.tex").read_text(encoding="utf-8")
    get = lambda k: re.search(k + r"=\{(.*?)\},?\n", cover).group(1)
    abstract = imp.convert(read("front/abstracts"))
    cn, en = abstract.split("# Abstract")
    (SRC / "00_摘要.md").write_text(
        f"<!-- title: {get('ctitle')} -->\n\n"
        f"<header class=\"title\">\n<h1>{get('ctitle')}</h1>\n"
        f"<p class=\"subtitle\">{get('cauthor')} · 导师 {get('csupervisor')} · {get('caffil')}</p>\n</header>\n\n<!--TOC-->\n\n"
        f"{cn.strip().replace('# 摘要', H2 % '摘要')}\n\n**关键词：**{get('ckeywords').replace(',', '；')}\n\n"
        f"{H2 % 'Abstract'}\n\n{en.strip()}\n\n**Keywords:** {get('ekeywords')}\n", encoding="utf-8")
    (SRC / "07_参考文献.md").write_text("# 参考文献\n\n<!--REFS-->\n", encoding="utf-8")
    (SRC / "refs.bib").write_text("\n".join((ROOT / "references" / f).read_text(encoding="utf-8")
                                            for f in ("startpaper.bib", "completed_work.bib")), encoding="utf-8")
    (SRC / "figs").mkdir(exist_ok=True)
    for path in sorted(imp.figs):
        pdf = ROOT / path
        subprocess.run(["pdftocairo", "-svg", str(pdf), str(SRC / "figs" / f"{pdf.stem}.svg")], check=True)
        print("转换", pdf.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
