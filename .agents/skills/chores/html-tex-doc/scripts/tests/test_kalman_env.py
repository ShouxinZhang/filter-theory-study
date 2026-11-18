"""Kalman 1960 经典论文所需的语法、环境、表格、脚注与文献区间单元测试。"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from htd.mdconv import compile_markdown_dir  # noqa: E402
from htd.numbering import auto_label_sections, number  # noqa: E402
from htd.render import render  # noqa: E402
from htd.workspace import read_paper_meta  # noqa: E402


def _make_bib(n: int = 8) -> str:
    return "".join(
        f"@article{{r0{i}, author={{Author {i}}}, title={{Paper {i}}}, journal={{J. Eng.}}, year={{195{i}}}}}\n"
        for i in range(1, n + 1)
    )


def _compile_and_render(files: dict[str, str]) -> tuple[str, dict[str, dict[str, str]], list[str]]:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        src, bld = root / "src", root / "build"
        src.mkdir()
        bld.mkdir()
        for rel, content in files.items():
            p = src / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        raw, errors = compile_markdown_dir(src)
        doc = auto_label_sections(raw)
        labels = number(doc, errors)
        body, _ = render(doc, labels, src, bld, False, errors)
        return body, labels, errors


class KalmanEnvAndSyntaxTest(unittest.TestCase):
    def test_pipe_table_protects_math_bars_code_escaped_pipe_and_xrefs(self):
        md = (
            "# 符号 {#sec:not}\n\n"
            "$$ {#eq:1}\nx = 1\n$$\n\n"
            "| 记号 | 条件与竖线 | 说明 |\n"
            "| :--- | :---: | ---: |\n"
            "| $x^{\\text{✫}}(t_1 \\mid t)$ | $a | b$ 与 $\\|\\bm{x}\\|$ | 见 `u | v`，转义 \\| 符，式 ({@eq:1|n}) |\n"
        )
        body, _, errors = _compile_and_render({"01.md": md})
        self.assertEqual(errors, [])
        self.assertIn('<table data-file="01.md" data-l1="7" data-l2="9">', body)
        self.assertIn('<tr data-file="01.md" data-l="7"><th style="text-align:left">', body)
        self.assertIn('<tr data-file="01.md" data-l="9">', body)
        self.assertEqual(body.count("<td"), 3)
        self.assertIn(r"\(x^{\text{✫}}(t_1 \mid t)\)", body)
        self.assertIn(r"\(a | b\)", body)
        self.assertIn(r"\(\|\bm{x}\|\)", body)
        self.assertIn("<code>u | v</code>", body)
        self.assertIn("转义 | 符", body)
        self.assertIn('<a class="xref" href="#eq-1">1</a>', body)

    def test_single_star_italic_preserves_math_and_bold(self):
        md = "正文 *单星斜体* 与 **双星加粗**，公式 $a * b * c$ 及代码 `x * y` 不受影响。\n"
        body, _, errors = _compile_and_render({"01.md": md})
        self.assertEqual(errors, [])
        self.assertIn("<em>单星斜体</em>", body)
        self.assertIn("<strong>双星加粗</strong>", body)
        self.assertIn(r"\(a * b * c\)", body)
        self.assertIn("<code>x * y</code>", body)

    def test_custom_env_numbering_lightweight_classes_and_non_p_lead(self):
        md = (
            "::: 定理 {#thm:1}\n\n第一定理正文。\n\n:::\n\n"
            "::: 定理 {#thm:1a num=1-a}\n\n*无需额外假设结论仍成立。*\n\n:::\n\n"
            "::: 定理 {#thm:2} 正交投影刻画\n\n第二定理正文。\n\n:::\n\n"
            "::: 问题 {#prob:I num=I}\n\n$$ {#eq:m}\nx(t+1) = \\Phi x(t)\n$$\n\n:::\n\n"
            "::: 评注 {#rem:c num=(c)}\n\n评注轻量样式正文。\n\n:::\n\n"
            "::: 算例 {#ex:1}\n\n- 算例首项为列表\n\n:::\n\n"
            "交叉验证：{@thm:1}，{@thm:1a}，{@thm:2}，{@prob:I}，{@rem:c}，{@ex:1}。\n"
        )
        body, labels, errors = _compile_and_render({"01.md": md})
        self.assertEqual(errors, [])
        self.assertEqual(labels["thm:1"]["text"], "定理 1")
        self.assertEqual(labels["thm:1a"]["text"], "定理 1-a")
        self.assertEqual(labels["thm:2"]["text"], "定理 2")
        self.assertEqual(labels["prob:I"]["text"], "问题 I")
        self.assertEqual(labels["rem:c"]["text"], "评注 (c)")
        self.assertEqual(labels["ex:1"]["text"], "算例 1")
        self.assertIn('<div class="thm thm--remark" id="rem-c"', body)
        self.assertIn('<div class="thm thm--example" id="ex-1"', body)
        self.assertIn('<p class="thm-lead"><span class="thmhead">问题 I</span><span class="thmtitle"></span></p>', body)
        self.assertIn('<p class="thm-lead"><span class="thmhead">算例 1</span><span class="thmtitle"></span></p>', body)
        self.assertIn('<span class="thmhead">定理 2</span><span class="thmtitle">（正交投影刻画）</span>', body)

    def test_xref_custom_text_and_undefined_error(self):
        md = (
            "# 最优估计 {#sec:opt}\n\n"
            "## K-10：正交余部记号 {#sec:k10}\n\n"
            "### 细节小节 {#sec:sub1}\n\n"
            "$$ {#eq:28}\n\\Delta = 1\n$$\n\n"
            "回引 {@eq:28}，裸号 ({@eq:28|n})，{@sec:opt|“最优估计”一节}，"
            "见{@sec:k10|校勘记 K-10}，以及{@sec:sub1|自定义三级小节}。\n"
        )
        body, _, errors = _compile_and_render({"01.md": md})
        self.assertEqual(errors, [])
        self.assertIn('<a class="xref" href="#eq-28">式 (1)</a>', body)
        self.assertIn('(<a class="xref" href="#eq-28">1</a>)', body)
        self.assertIn('<a class="xref" href="#sec-opt">“最优估计”一节</a>', body)
        self.assertIn('<a class="xref" href="#sec-k10">校勘记 K-10</a>', body)
        self.assertIn('<a class="xref" href="#sec-sub1">自定义三级小节</a>', body)

        _, _, bad_errors = _compile_and_render({"01.md": "悬空引用{@sec:missing|校勘记 K-99}。\n"})
        self.assertTrue(any("sec:missing" in e for e in bad_errors))

    def test_bib_order_file_and_consecutive_range_merge(self):
        files = {
            "main.md": "---\ntitle: Kalman 1960\nbib: refs.bib\nbib_order: file\n---\n<!--include 01.md-->\n",
            "refs.bib": _make_bib(8),
            "01.md": (
                "先引单篇[@r08]，再引连续六篇[@r02,r03,r04,r05,r06,r07]，"
                "两篇相邻[@r05,r06]保持逗号，混合[@r01,r03,r04,r05,r08]。\n\n<!--REFS-->\n"
            ),
        }
        with tempfile.TemporaryDirectory() as d:
            src = Path(d)
            for k, v in files.items():
                (src / k).write_text(v, encoding="utf-8")
            self.assertEqual(read_paper_meta(src).bib_order, "file")
        body, _, errors = _compile_and_render(files)
        self.assertEqual(errors, [])
        self.assertIn('[<a class="cite" href="#ref-r08">8</a>]', body)
        self.assertIn('[<a class="cite" href="#ref-r02">2</a>–<a class="cite" href="#ref-r07">7</a>]', body)
        self.assertIn('[<a class="cite" href="#ref-r05">5</a>,<a class="cite" href="#ref-r06">6</a>]', body)
        self.assertIn(
            '[<a class="cite" href="#ref-r01">1</a>,<a class="cite" href="#ref-r03">3</a>–<a class="cite" href="#ref-r05">5</a>,<a class="cite" href="#ref-r08">8</a>]',
            body,
        )
        self.assertEqual(body.count('<li id="ref-r0'), 8)

    def test_footnotes_bidirectional_cross_file_and_missing_check(self):
        files = {
            "main.md": "---\ntitle: 脚注测试\n---\n<!--include 00.md-->\n<!--include 04.md-->\n<!--include 05.md-->\n",
            "00.md": "标题[^1]与机构[^2]。\n",
            "04.md": "[^1]: 资助说明 *AFOSR*。\n\n[^2]: 巴尔的摩地址。\n\n<!--FOOTNOTES-->\n",
            "05.md": "# 校勘记 {#sec:err}\n\n校勘正文。\n",
        }
        body, _, errors = _compile_and_render(files)
        self.assertEqual(errors, [])
        self.assertIn('<sup class="fnref"><a class="xref" href="#fn-1" id="fnref-1">[1]</a></sup>', body)
        self.assertIn('<li id="fn-1">资助说明 <em>AFOSR</em>. <a class="fn-back" href="#fnref-1" aria-label="返回正文">↩</a></li>'.replace("</em>.", "</em>。"), body)
        self.assertLess(body.index('<section class="footnotes">'), body.index('id="sec-err"'))

        auto_body, _, auto_err = _compile_and_render({"01.md": "正文[^a]。\n\n[^a]: 自动追加文末。\n"})
        self.assertEqual(auto_err, [])
        self.assertTrue(auto_body.rstrip().endswith("</section>"))

        _, _, miss_err = _compile_and_render({"01.md": "正文引用未定义脚注[^99]。\n"})
        self.assertTrue(any("[^99]" in e for e in miss_err))


if __name__ == "__main__":
    unittest.main()
