#!/usr/bin/env python3
"""html-tex-doc 的单元与回归测试。运行：python3 -m unittest discover -s <scripts>/tests -v"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

from htd import assets, mathpre, texfig  # noqa: E402
from htd.bib import fmt_ref, parse_bib  # noqa: E402
from htd.build import build_project  # noqa: E402
from htd.cli import cmd_init  # noqa: E402
from htd.mdconv import MarkdownCompiler  # noqa: E402
from htd.numbering import auto_label_sections, number  # noqa: E402
from htd.paths import ASSETS_DIR  # noqa: E402

HAS_TEX = bool(shutil.which("xelatex") and shutil.which("dvisvgm"))
BIB = "@article{k1, author={Kalman, Rudolf}, title={A new approach}, journal={J. Basic Eng.}, year={1960}}\n" \
      "@book{k2, author={{李天成} and {范红旗}}, title={粒子滤波}, publisher={某出版社}, year=2015}\n"


class Numbering(unittest.TestCase):
    DOC = ('<h2 data-label="sec:a">A</h2><div class="eq" data-label="eq:1">\\[x\\]</div>'
           '<h3>无标签小节</h3><div class="eq" data-label="eq:2">\\[y\\]</div>'
           '<div class="thm" data-kind="引理" data-label="lem:1"><p>t</p></div>'
           '<figure class="tbl" data-label="tab:1"><figcaption>c</figcaption></figure>')

    def test_numbers_follow_document_order(self):
        errors: list[str] = []
        labels = number(auto_label_sections(self.DOC), errors)
        self.assertEqual(errors, [])
        self.assertEqual(labels["sec:a"]["num"], "1")
        self.assertEqual(labels["eq:2"]["text"], "式 (2)")
        self.assertEqual(labels["lem:1"]["text"], "引理 1")
        self.assertEqual(labels["tab:1"]["text"], "表 1")
        self.assertIn("1.1", [v["num"] for v in labels.values()])

    def test_duplicate_label_is_an_error(self):
        errors: list[str] = []
        number(self.DOC + '<div class="eq" data-label="eq:1">\\[z\\]</div>', errors)
        self.assertTrue(any("eq:1" in e for e in errors))


class Bib(unittest.TestCase):
    def test_parse_and_format(self):
        bib = parse_bib(BIB)
        self.assertEqual(set(bib), {"k1", "k2"})
        self.assertEqual(bib["k2"]["year"], "2015")
        ref = fmt_ref(bib["k1"])
        self.assertIn("Rudolf Kalman", ref)
        self.assertIn("<em>J. Basic Eng.</em>", ref)
        self.assertIn("李天成", fmt_ref(bib["k2"]))


class Markdown(unittest.TestCase):
    def compile(self, text: str) -> tuple[str, list[str]]:
        c = MarkdownCompiler(parse_bib(BIB))
        return c.convert(text, "t.md"), c.errors

    def test_blocks(self):
        html_, errors = self.compile(
            "# 章 {#sec:x}\n\n正文 $a<b$ 见[@k2,k1]。\n\n$$ {#eq:m}\nx &= 1\n$$\n\n::: 定理 {#thm:t} 名称\n\n内容\n\n:::\n\n- 甲\n- 乙\n")
        self.assertEqual(errors, [])
        self.assertRegex(html_, r'<h2[^>]*data-label="sec:x"')
        self.assertIn(r"\(a&lt;b\)", html_)
        self.assertRegex(html_, r'<div class="eq"[^>]*data-label="eq:m"')
        self.assertIn("x &amp;= 1", html_)
        self.assertRegex(html_, r'<div class="thm"[^>]*data-kind="定理"[^>]*data-label="thm:t"')
        self.assertRegex(html_, r"<ul[^>]*>.*甲.*乙.*</ul>")
        self.assertRegex(html_, r'href="#ref-k2"[^>]*>1<')   # 文献按首次出现编号
        self.assertRegex(html_, r'data-file="t\.md"')         # 源码锚点

    def test_unknown_citation_is_reported(self):
        _, errors = self.compile("见[@nope]。\n")
        self.assertTrue(any("nope" in e for e in errors))


class Assets(unittest.TestCase):
    LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|border-radius:[^;]*\dpx|z-index:\s*\d|\"[A-Z][^\"]* (?:CJK|Mono|Sans|Serif)[^\"]*\"")
    LONG_OK = {"70_workbench.js"}  # 含一个 323 行的 DOM 构建函数，拆它需要改写函数体，另行处理

    def test_literals_live_only_in_tokens(self):
        for f in assets.part_files("style.css"):
            if f.name == "00_tokens.css":
                continue
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                self.assertIsNone(self.LITERAL.search(line), f"{f.name}:{i} 出现了应放进 00_tokens.css 的字面量：{line.strip()[:80]}")

    def test_bundle_order_and_core(self):
        css = assets.bundle("style.css")
        self.assertLess(css.index("--font-serif"), css.index("main.doc-pane"))
        for name in ("reader.js", "editor.js"):
            self.assertTrue(assets.bundle(name).startswith((ASSETS_DIR / "js/core.js").read_text(encoding="utf-8")))

    def test_source_files_stay_small(self):
        files = [p for n in ("style.css", "reader.js", "editor.js") for p in assets.part_files(n)]
        files += list((SCRIPTS / "htd").rglob("*.py"))
        for f in files:
            n = len(f.read_text(encoding="utf-8").splitlines())
            if f.name not in self.LONG_OK:
                self.assertLessEqual(n, 300, f"{f} 有 {n} 行")

    def test_ui_classes_used_by_scripts_are_defined(self):
        """脚本与目录生成器里用到的 ui-* 组件类，都必须在 08_components.css 里有定义。"""
        css = (ASSETS_DIR / "css" / "08_components.css").read_text(encoding="utf-8")
        defined = set(re.findall(r"\.(ui-[a-z-]+)", css))
        sources = [p for n in ("reader.js", "editor.js") for p in assets.part_files(n)] + [SCRIPTS / "htd" / "toc.py"]
        used = {c for p in sources for c in re.findall(r"\b(ui-[a-z]+(?:--[a-z]+)?)\b", p.read_text(encoding="utf-8"))}
        self.assertTrue(used, "没有扫描到任何 ui-* 类")
        self.assertEqual(used - defined, set())

    def test_project_overrides(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d)
            (src / "theme.css").write_text(":root{--accent:red}", encoding="utf-8")
            css = assets.bundle("style.css", src)
            self.assertTrue(css.rstrip().endswith(":root{--accent:red}"))
            (src / "style.css").write_text("body{}", encoding="utf-8")   # 旧工程的整份覆盖仍然生效
            self.assertEqual(assets.bundle("style.css", src), "body{}")


class TexFigureCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src, self.build = Path(self.tmp.name) / "src", Path(self.tmp.name) / "build"
        (self.src / "figs").mkdir(parents=True)
        self.build.mkdir()
        self.fig = self.src / "figs" / "a.tex"
        self.fig.write_text("\\input{common}\\cref{eq:1}", encoding="utf-8")
        self.labels("式~(1)", "式~(2)")

    def tearDown(self):
        self.tmp.cleanup()

    def labels(self, one: str, two: str) -> None:
        (self.build / "labels.tex").write_text(f"\\lbl{{eq:1}}{{{one}}}{{eq-1}}\n\\lbl{{eq:2}}{{{two}}}{{eq-2}}\n", encoding="utf-8")

    def key(self) -> str:
        return texfig.cache_key(self.fig, self.src, self.build)

    def test_key_depends_on_content_not_mtime(self):
        k = self.key()
        os.utime(self.fig, (1, 1))
        self.assertEqual(self.key(), k)
        self.fig.write_text(self.fig.read_text(encoding="utf-8") + "%", encoding="utf-8")
        self.assertNotEqual(self.key(), k)

    def test_only_referenced_labels_matter(self):
        k = self.key()
        self.labels("式~(1)", "式~(9)")      # 无关编号变化
        self.assertEqual(self.key(), k)
        self.labels("式~(3)", "式~(9)")      # 被引用的编号变化
        self.assertNotEqual(self.key(), k)


@unittest.skipIf(mathpre.available(), "公式预渲染依赖未安装")
class MathPrerender(unittest.TestCase):
    BODY = r"<p>设 \(a&lt;b\)，则</p><div class=\"eq\">\[ x^2 \tag{1} \]</div><code>\(保持原样\)</code>".replace('\\"', '"')

    def test_cache_is_reliable(self):
        with tempfile.TemporaryDirectory() as d:
            b, o = Path(d) / "build", Path(d) / "out"
            out1, css1, st1 = mathpre.prerender(self.BODY, {}, b, o)
            out2, css2, st2 = mathpre.prerender(self.BODY, {}, b, o)
            self.assertEqual((st1["miss"], st2["miss"], st2["hit"]), (2, 0, 2))
            self.assertEqual((out1, css1), (out2, css2))
            self.assertEqual(out1.count("<mjx-container"), 2)
            self.assertIn(r"<code>\(保持原样\)</code>", out1)
            self.assertEqual(st1["errors"], 0)
            out3, _, st3 = mathpre.prerender(self.BODY, {"R": "\\mathbb{R}"}, b, o)   # 宏变了，全部失效
            self.assertEqual(st3["miss"], 2)


@unittest.skipUnless(HAS_TEX, "需要 xelatex 与 dvisvgm")
class EndToEnd(unittest.TestCase):
    def test_academic_template_builds_reproducibly(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertEqual(cmd_init(SimpleNamespace(dir=str(root), title="测试", preset="academic-md", force=False)), 0)
            self.assertFalse((root / "src" / "reader.js").exists())     # 运行时资源不再复制进工程
            pages = []
            for _ in range(2):
                rc, msg, _body = build_project(root / "src", root / "build", root / "out")
                self.assertEqual(rc, 0, msg)
                pages.append((root / "out" / "index.html").read_bytes())
            self.assertEqual(pages[0], pages[1])
            for f in ("style.css", "reader.js"):
                self.assertTrue((root / "out" / f).stat().st_size > 1000)


if __name__ == "__main__":
    unittest.main()
