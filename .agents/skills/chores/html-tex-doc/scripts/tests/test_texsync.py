#!/usr/bin/env python3
"""texsync 双向转换、最小差异回写与门禁测试（G1/G2/G4/G5）。"""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import re
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import htd  # noqa: E402

if (SCRIPTS / "htd").is_dir() and str(SCRIPTS / "htd") not in htd.__path__:
    htd.__path__.insert(0, str(SCRIPTS / "htd"))

from htd.texsync import (  # noqa: E402
    KALMAN_SPEC,
    SyncPair,
    grab_braced,
    md_inline_to_tex,
    md_to_tex,
    parse_md_units,
    patch_paragraph_minimal,
    patch_tex,
    run_export_cli,
    run_import_cli,
    tex_inline_to_md,
    tex_to_md,
)


def _find_repo_root() -> Path:
    cur = Path(__file__).resolve()
    for p in cur.parents:
        if (p / "co-work 资产/tex-论文/论文集/线性滤波与预测1960/html/src/main.md").is_file():
            return p
    raise RuntimeError("未找到仓库根目录及 1960 论文语料")


REPO_ROOT = _find_repo_root()
KALMAN_SRC = REPO_ROOT / "co-work 资产/tex-论文/论文集/线性滤波与预测1960/html/src"


class TestInlineAndBrace(unittest.TestCase):
    def test_grab_braced_nested_and_escaped(self) -> None:
        s = r"\emph{前文 \hyperref[sec:appendix]{附录 \{A\}} 后文}尾"
        res = grab_braced(s, 5)
        self.assertIsNotNone(res)
        assert res is not None
        self.assertEqual(res[0], r"前文 \hyperref[sec:appendix]{附录 \{A\}} 后文")
        self.assertEqual(s[res[1]:], "尾")
        self.assertIsNone(grab_braced("{未闭合", 0))

    def test_inline_bijection_and_tilde_variants(self) -> None:
        samples = [
            "参见{@eq:12}，式 ({@eq:12|n})–({@eq:14|n}) 与 ({@eq:29|n}–{@eq:30|n})。",
            "由{@thm:1}，{@cor:1}，{@prob:I}，{@rem:a}，{@ex:1}，{@fig:3}，{@tab:1} 与{@sec:intro}。",
            "*全文论述基本自包含；基本概念在{@sec:appendix|附录}中回顾。*",
            "含 *$n$ 维向量*，**加粗 `code_1` 文本**，文献[@r01,r02][^3] 及符号 C_3(t) & 50% #1。",
        ]
        for md in samples:
            with self.subTest(md=md):
                self.assertEqual(tex_inline_to_md(md_inline_to_tex(md)), md)
        self.assertEqual(tex_inline_to_md(r"方程~\eqref{eq:35} 与公式~\eqref{eq:12}"), "方程 ({@eq:35|n}) 与公式 ({@eq:12|n})")
        self.assertEqual(tex_inline_to_md(r"式~\eqref{eq:35} 区别于 式 \eqref{eq:35}"), "{@eq:35} 区别于 式 ({@eq:35|n})")

    def test_minimal_paragraph_preserves_neighbors(self) -> None:
        orig_tex = (
            "第一句讨论方程~\\eqref{eq:35} 的收敛性质， % 原稿行尾注记 $x$\n"
            "手工折行后继续阐述。第二句为旧表述。第三句引用公式~\\eqref{eq:12}。 % 句末注记"
        )
        new_md = (
            "第一句讨论方程 ({@eq:35|n}) 的收敛性质，\n"
            "手工折行后继续阐述。第二句已改为新表述并补充[@r29]。第三句引用公式 ({@eq:12|n})。"
        )
        patched = patch_paragraph_minimal(orig_tex, new_md)
        self.assertIn("方程~\\eqref{eq:35} 的收敛性质， % 原稿行尾注记 $x$\n手工折行后继续阐述。", patched)
        self.assertIn(r"第二句已改为新表述并补充\cite{r29}。", patched)
        self.assertIn("第三句引用公式~\\eqref{eq:12}。 % 句末注记", patched)
        self.assertEqual(tex_inline_to_md(patched), new_md)


class TestKalmanCorpusRoundtrip(unittest.TestCase):
    def test_all_chapters_and_abstract_byte_identical(self) -> None:
        chapters = sorted(KALMAN_SRC.glob("[0-9]*.md"))
        self.assertEqual(len(chapters), 6)
        for p in chapters:
            md = p.read_text(encoding="utf-8")
            with self.subTest(file=p.name):
                tex = md_to_tex(md)
                self.assertEqual(tex_to_md(tex), md)
                res = patch_tex(tex, md, filename=p.stem + ".tex")
                self.assertTrue(res.ok)
                self.assertEqual(res.patched_tex, tex)
                self.assertEqual(res.diff_text, "")
                for u in parse_md_units(md):
                    self.assertEqual(tex_to_md(u.tex_text), u.md_text)
                    if u.kind not in ("env_open", "env_close"):
                        self.assertEqual(tex_to_md(md_to_tex(u.md_text)), u.md_text)

        main_md = (KALMAN_SRC / "main.md").read_text(encoding="utf-8")
        i0 = main_md.index("</header>") + len("</header>")
        i1 = main_md.index("<!--TOC-->")
        abs_slice = main_md[i0:i1].strip("\n")
        self.assertEqual(tex_to_md(md_to_tex(abs_slice)), abs_slice)
        self.assertEqual(tex_to_md(md_to_tex(abs_slice + "\n")), abs_slice + "\n")

    def test_authentic_tex_with_table_float_comments_and_tilde(self) -> None:
        md_03 = (KALMAN_SRC / "03_对偶问题与应用算例.md").read_text(encoding="utf-8")
        base_tex = md_to_tex(md_03)
        rich_tex = "% 第 3 章文件头独立注释\n" + base_tex
        rich_tex = rich_tex.replace(r"方程 \eqref{eq:", r"方程~\eqref{eq:")
        rich_tex = rich_tex.replace(
            r"\begin{theorem}[对偶定理]\label{thm:4}",
            "% 对偶核心定理\n\\begin{theorem}[对偶定理]\\label{thm:4}",
        )
        rich_tex = rich_tex.replace(
            r"\begin{tabularx}{\textwidth}{cXX}",
            "% 三线表局部排版微调\n\\renewcommand{\\arraystretch}{1.15}\n\\begin{tabularx}{\\textwidth}{cXX}",
        )
        self.assertIn(r"\begin{table}[htbp]", rich_tex)
        self.assertIn(r"\label{tab:1}", rich_tex)
        self.assertIn(r"方程~\eqref{eq:35}", rich_tex)
        self.assertEqual(tex_to_md(rich_tex), md_03)

        edited_md = md_03.replace("如何进一步发掘并拓展这些内在联系，仍有大量工作留待完成。", "如何进一步拓展这些深刻联系，仍待后续研究。")
        res = patch_tex(rich_tex, edited_md, filename="03_对偶问题与应用算例.tex")
        self.assertTrue(res.ok)
        self.assertIn("% 第 3 章文件头独立注释\n", res.patched_tex)
        self.assertIn("% 对偶核心定理\n\\begin{theorem}[对偶定理]\\label{thm:4}", res.patched_tex)
        self.assertIn(r"\renewcommand{\arraystretch}{1.15}", res.patched_tex)
        self.assertIn(r"方程~\eqref{eq:35}", res.patched_tex)
        self.assertIn("本文从“状态”观点出发重新表述并求解了线性最优估计问题。", res.patched_tex)
        self.assertEqual(tex_to_md(res.patched_tex), edited_md)


class TestSpacingListAndGatekeeper(unittest.TestCase):
    def test_equation_tight_and_loose_spacing_sync(self) -> None:
        orig_tex = "前导段\n\\begin{equation}\\label{eq:1}\nx = 1\n\\end{equation}\n紧邻续段。\n"
        self.assertEqual(tex_to_md(orig_tex), "前导段\n$$ {#eq:1}\nx = 1\n$$\n紧邻续段。\n")
        loose_md = "前导段\n\n$$ {#eq:1}\nx = 1\n$$\n\n独立新段。\n"
        res1 = patch_tex(orig_tex, loose_md)
        self.assertTrue(res1.ok)
        self.assertEqual(res1.patched_tex, "前导段\n\n\\begin{equation}\\label{eq:1}\nx = 1\n\\end{equation}\n\n独立新段。\n")
        tight_again = "前导段\n$$ {#eq:1}\nx = 1\n$$\n独立新段。\n"
        res2 = patch_tex(res1.patched_tex, tight_again)
        self.assertTrue(res2.ok)
        self.assertEqual(res2.patched_tex, "前导段\n\\begin{equation}\\label{eq:1}\nx = 1\n\\end{equation}\n独立新段。\n")

    def test_list_item_minimal_patch(self) -> None:
        orig_tex = (
            "\\begin{itemize}\n"
            "\\item 第一项含方程~\\eqref{eq:1}。 % 保留项注释\n"
            "\\item 第二项旧文字。\n"
            "\\end{itemize}\n"
        )
        new_md = "- 第一项含方程 ({@eq:1|n})。\n- 第二项新文字。\n"
        res = patch_tex(orig_tex, new_md)
        self.assertTrue(res.ok)
        self.assertIn("\\item 第一项含方程~\\eqref{eq:1}。 % 保留项注释", res.patched_tex)
        self.assertIn("\\item 第二项新文字。", res.patched_tex)

    def test_manual_gatekeeper_and_zero_byte_cli_apply(self) -> None:
        with tempfile.TemporaryDirectory(prefix="texsync_") as tmp:
            root = Path(tmp)
            main_orig = (KALMAN_SRC / "main.md").read_text(encoding="utf-8")
            md03_orig = (KALMAN_SRC / "03_对偶问题与应用算例.md").read_text(encoding="utf-8")
            md04_orig = (KALMAN_SRC / "04_参考文献与附录.md").read_text(encoding="utf-8")
            i0 = main_orig.index("</header>") + len("</header>")
            i1 = main_orig.index("<!--TOC-->")
            abs_tex_orig = "% 摘要注释\n" + md_to_tex(main_orig[i0:i1].strip("\n") + "\n")
            tex03_orig = "% 第三章\n" + md_to_tex(md03_orig).replace(r"方程 \eqref{eq:", r"方程~\eqref{eq:")
            tex04_orig = "% 第四章\n" + md_to_tex(md04_orig)

            abs_tex_p, tex03_p, tex04_p = root / "abstract.tex", root / "03.tex", root / "04.tex"
            main_md_p, md03_p, md04_p = root / "main.md", root / "03.md", root / "04.md"
            abs_tex_p.write_text(abs_tex_orig, encoding="utf-8")
            tex03_p.write_text(tex03_orig, encoding="utf-8")
            tex04_p.write_text(tex04_orig, encoding="utf-8")
            main_md_p.write_text(main_orig, encoding="utf-8")
            md03_p.write_text(md03_orig, encoding="utf-8")
            md04_p.write_text(md04_orig, encoding="utf-8")

            pairs = [
                SyncPair(abs_tex_p, main_md_p, md_slice=("</header>", "<!--TOC-->"), expected_md_frame=main_orig),
                SyncPair(tex03_p, md03_p),
                SyncPair(tex04_p, md04_p),
            ]
            self.assertEqual(run_import_cli(pairs, argv=["--check"]), 0)

            # G4 场景 1: 04.md 合法修改 + 03.md 篡改 tab:1 表格 -> 整体拒绝且全部文件 0 字节写入
            md04_p.write_text(md04_orig.replace("不代表学会立场。", "不代表学会官方立场。"), encoding="utf-8")
            md03_p.write_text(md03_orig.replace("问题 I 与问题 II 的对偶关系", "篡改表格标题"), encoding="utf-8")
            snap = (abs_tex_p.read_bytes(), tex03_p.read_bytes(), tex04_p.read_bytes())
            err_buf = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err_buf):
                rc = run_export_cli(pairs, argv=["--apply"])
            self.assertNotEqual(rc, 0)
            self.assertIn("tab:1", err_buf.getvalue())
            self.assertIn("需人工处理", err_buf.getvalue())
            self.assertEqual((abs_tex_p.read_bytes(), tex03_p.read_bytes(), tex04_p.read_bytes()), snap)

            # G4 场景 2: 新增 ::: 定理 环境 -> 拒绝且 0 字节写入
            md03_p.write_text(md03_orig + "\n::: 定理 {#thm:extra}\n\n新增定理。\n\n:::\n", encoding="utf-8")
            err_buf = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err_buf):
                rc2 = run_export_cli(pairs, argv=["--apply"])
            self.assertNotEqual(rc2, 0)
            self.assertIn("需人工处理", err_buf.getvalue())
            self.assertEqual((abs_tex_p.read_bytes(), tex03_p.read_bytes(), tex04_p.read_bytes()), snap)

            # G4 场景 3: 篡改 main.md 的 include 列表 -> 框架守卫拦截且 0 字节写入
            md03_p.write_text(md03_orig, encoding="utf-8")
            main_md_p.write_text(main_orig + "<!--include 06_extra.md-->\n", encoding="utf-8")
            err_buf = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err_buf):
                rc3 = run_export_cli(pairs, argv=["--apply"])
            self.assertNotEqual(rc3, 0)
            self.assertIn("main.md", err_buf.getvalue())
            self.assertEqual((abs_tex_p.read_bytes(), tex03_p.read_bytes(), tex04_p.read_bytes()), snap)

            # G1 + G2 场景: 恢复合法修改 (main.md 摘要段 + 04.md 段落)，预览不写盘，--apply 写盘后重导入零差异
            main_edited = main_orig.replace("证明了滤波问题是无噪声调节器问题的对偶问题。", "严格证明了滤波问题与无噪声调节器问题的对偶性。")
            main_md_p.write_text(main_edited, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run_export_cli(pairs, argv=[]), 0)
            self.assertEqual((abs_tex_p.read_bytes(), tex03_p.read_bytes(), tex04_p.read_bytes()), snap)

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run_export_cli(pairs, argv=["--apply"]), 0)
            self.assertEqual(tex03_p.read_bytes(), snap[1])  # 未改动文件完全未碰
            self.assertTrue(abs_tex_p.read_text(encoding="utf-8").startswith("% 摘要注释\n"))
            self.assertEqual(run_import_cli(pairs, argv=["--check"]), 0)


class TestLineCountBudget(unittest.TestCase):
    def test_all_texsync_python_files_within_300_lines(self) -> None:
        texsync_dir = Path(htd.texsync.__file__).resolve().parent
        py_files = [*sorted(texsync_dir.glob("*.py")), Path(__file__).resolve()]
        budgets = {"__init__.py": 40, "inline.py": 240, "codec.py": 270, "diffpatch.py": 260, "test_texsync.py": 270}
        for f in py_files:
            lines = len(f.read_text(encoding="utf-8").splitlines())
            self.assertLessEqual(lines, 300, f"{f.name} 超过 300 行硬门禁: {lines}")
            if f.name in budgets:
                self.assertLessEqual(lines, budgets[f.name], f"{f.name} 超过子目标 {budgets[f.name]} 行: {lines}")


if __name__ == "__main__":
    unittest.main()
