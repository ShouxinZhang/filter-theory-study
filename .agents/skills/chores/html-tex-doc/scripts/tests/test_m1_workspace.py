"""M1 工作区与 include 编译单元测试（可直接并入 scripts/tests/test_htd.py）。"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from htd.mdconv import compile_markdown_dir  # noqa: E402
from htd.server.files import _list_editable_files  # noqa: E402
from htd.workspace import discover_papers, parse_frontmatter, read_paper_meta  # noqa: E402

SAMPLE_BIB = "@article{k1, author={Kalman, Rudolf}, title={A new approach}, journal={J. Basic Eng.}, year={1960}}\n"


class WorkspaceAndInclude(unittest.TestCase):
    def test_parse_frontmatter_and_line_alignment(self):
        raw = '---\n# 导言注释\ntitle: "滤波工作区"\nmacros: \'custom.tex\'\n\nbib: sub/refs.bib\n---\n\n# 第一章 {#sec:c1}\n\n导语段落\n'
        meta, rest, start_ln = parse_frontmatter(raw)
        self.assertEqual(meta, {"title": "滤波工作区", "macros": "custom.tex", "bib": "sub/refs.bib"})
        self.assertEqual((start_ln, rest.startswith("\n# 第一章")), (8, True))
        self.assertEqual(parse_frontmatter("---\ntitle: x\n正文")[2], 1)
        self.assertEqual(parse_frontmatter("普通正文\n第二行")[2], 1)
        with tempfile.TemporaryDirectory() as d:
            src = Path(d)
            (src / "chapters").mkdir()
            (src / "chapters" / "01.md").write_text("## 子节 {#sec:s1}\n\n章节正文\n", encoding="utf-8")
            (src / "main.md").write_text(
                "---\ntitle: 行号测试\n---\n\n# 导言章 {#sec:intro}\n\n<!--include chapters/01.md-->\n\n尾声段落\n",
                encoding="utf-8",
            )
            doc, errors = compile_markdown_dir(src)
            self.assertEqual(errors, [])
            self.assertIn('data-file="main.md" data-l="5" data-l1="5" data-l2="5"', doc)
            self.assertIn('data-file="chapters/01.md" data-l="1" data-l1="1" data-l2="1"', doc)
            self.assertIn('<span class="sl" data-file="main.md" data-l="9">尾声段落</span>', doc)

    def test_main_include_subdirs_bib_and_file_order(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d)
            (src / "chapters").mkdir()
            (src / "bib").mkdir()
            (src / "bib" / "my.bib").write_text(SAMPLE_BIB, encoding="utf-8")
            (src / "00_摘要.md").write_text('<p class="h2">摘要</p>\n\n摘要引用[@k1]。\n', encoding="utf-8")
            (src / "chapters" / "01.md").write_text("# 正文 {#sec:m}\n\n### 小节 {#sec:sub}\n\n回引{@sec:sub}。\n", encoding="utf-8")
            (src / "main.md").write_text(
                "---\ntitle: 子目录测试\nmacros: macros.tex\nbib: bib/my.bib\n---\n\n"
                "<!--include 00_摘要.md-->\n\n<!--include chapters/01.md-->\n\n<!--REFS-->\n",
                encoding="utf-8",
            )
            pmeta = read_paper_meta(src)
            self.assertEqual((pmeta.title, pmeta.macros, pmeta.bib, pmeta.entry), ("子目录测试", "macros.tex", "bib/my.bib", "main.md"))
            doc, errors = compile_markdown_dir(src)
            self.assertEqual(errors, [])
            for frag in ('href="#ref-k1"', '<ol class="refs"><li id="ref-k1">', '<a class="xref" href="#sec-sub">第 1.0.1 节</a>'):
                self.assertIn(frag, doc)
            self.assertEqual([it["path"] for it in _list_editable_files(src)][:3], ["main.md", "00_摘要.md", "chapters/01.md"])

    def test_include_errors_missing_escape_self_and_nested(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src"
            (src / "chapters").mkdir(parents=True)
            (Path(d) / "outside.md").write_text("越界\n", encoding="utf-8")
            (src / "chapters" / "nested.md").write_text("<!--include 02.md-->\n", encoding="utf-8")
            (src / "main.md").write_text(
                "<!--include missing.md-->\n<!--include ../outside.md-->\n<!--include main.md-->\n<!--include chapters/nested.md-->\n",
                encoding="utf-8",
            )
            _, errors = compile_markdown_dir(src)
            self.assertEqual(len(errors), 4)
            for kw in ("missing.md", "越界", "自包含", "嵌套 include"):
                self.assertTrue(any(kw in e for e in errors), kw)

    def test_legacy_without_main_md_compatible(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d)
            (src / "refs.bib").write_text(SAMPLE_BIB, encoding="utf-8")
            (src / "00_a.md").write_text("<!-- title: 旧版工程 -->\n\n第一段[@k1]。\n", encoding="utf-8")
            (src / "01_b.md").write_text("# 文献\n\n<!--REFS-->\n", encoding="utf-8")
            self.assertEqual((read_paper_meta(src).title, read_paper_meta(src).entry), ("旧版工程", "*.md"))
            doc_legacy, err_legacy = compile_markdown_dir(src)
            (src / "main.md").write_text("---\ntitle: 旧版工程\nbib: refs.bib\n---\n\n<!--include 00_a.md-->\n\n<!--include 01_b.md-->\n", encoding="utf-8")
            doc_main, err_main = compile_markdown_dir(src)
            self.assertEqual((err_legacy, err_main, doc_legacy == doc_main), ([], [], True))

    def test_discover_papers_two_levels(self):
        with tempfile.TemporaryDirectory() as d:
            lib = Path(d)
            for rel, fn, body in (
                ("alpha/src", "main.md", "---\ntitle: 论文甲\n---\n"),
                ("alpha/sub/src", "main.md", "---\ntitle: 不应递归\n---\n"),
                ("非线性滤波/html/src", "00.md", "<!-- title: 滤波论文 -->\n"),
                ("组/basic-doc/src", "doc.html", "<h1>HTML 标题</h1>\n"),
                (".git/p/src", "main.md", "---\ntitle: 忽略\n---\n"),
                ("public-references/p/src", "main.md", "---\ntitle: 忽略\n---\n"),
                ("outputs/p/src", "main.md", "---\ntitle: 忽略\n---\n"),
                ("a/b/deep/src", "main.md", "---\ntitle: 忽略\n---\n"),
            ):
                (lib / rel).mkdir(parents=True)
                (lib / rel / fn).write_text(body, encoding="utf-8")
            self.assertEqual(discover_papers(lib), [
                {"id": "alpha", "title": "论文甲", "entry": "main.md"},
                {"id": "组/basic-doc", "title": "HTML 标题", "entry": "doc.html"},
                {"id": "非线性滤波/html", "title": "滤波论文", "entry": "*.md"},
            ])


if __name__ == "__main__":
    unittest.main()
