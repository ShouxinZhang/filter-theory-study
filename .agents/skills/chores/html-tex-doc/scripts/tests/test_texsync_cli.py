#!/usr/bin/env python3
"""texsync CLI (import-tex / export-tex) 与 scaffold_tex_project 端到端测试套件。"""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest

SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import htd  # noqa: E402

if (SCRIPTS / "htd").is_dir() and str(SCRIPTS / "htd") not in htd.__path__:
    htd.__path__.insert(0, str(SCRIPTS / "htd"))

from htd import cli  # noqa: E402
from htd.texsync.manifest import execute_export, execute_import  # noqa: E402
from htd.texsync.scaffold import scaffold_tex_project  # noqa: E402


def _find_repo_root() -> Path:
    cur = Path(__file__).resolve()
    for p in cur.parents:
        if (p / "co-work 资产/tex-论文/论文集/线性滤波与预测1960/html/src/main.md").is_file():
            return p
    raise RuntimeError("未找到仓库根目录及 1960 论文语料")


REPO_ROOT = _find_repo_root()
KALMAN_HTML_SRC = REPO_ROOT / "co-work 资产/tex-论文/论文集/线性滤波与预测1960/html/src"


def _run_cli(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cli.main(argv)
    return rc, out.getvalue(), err.getvalue()


class TestScaffoldAndKalmanRoundtrip(unittest.TestCase):
    def test_kalman_1960_init_tex_under_500ms_and_zero_diff_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory(prefix="texsync_c_1960_") as tmp:
            root = Path(tmp)
            shutil.copytree(KALMAN_HTML_SRC, root / "html" / "src")

            # 默认预览不写盘
            rc_pre, out_pre, _ = _run_cli(["export-tex", str(root), "--init-tex"])
            self.assertEqual(rc_pre, 0)
            self.assertIn("main.tex", out_pre)
            self.assertFalse((root / "main.tex").exists())
            self.assertFalse((root / "html" / "texsync.json").exists())

            # 智能路径归一（传入父目录 root）+ 毫秒级生成完整 TeX 工程
            t0 = time.perf_counter()
            rc, _, err = _run_cli(["export-tex", str(root), "--init-tex", "--apply"])
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            self.assertEqual(rc, 0, err)
            self.assertLess(elapsed_ms, 500.0, f"scaffold 耗时超标: {elapsed_ms:.1f} ms")

            for rel in ("main.tex", "preamble.tex", "build.sh", ".gitignore", "sections/abstract.tex", "sections/03_对偶问题与应用算例.tex"):
                self.assertTrue((root / rel).is_file(), f"缺少文件: {rel}")
            self.assertTrue(os.access(root / "build.sh", os.X_OK))
            self.assertTrue((root / "html" / "texsync.json").is_file())
            main_tex = (root / "main.tex").read_text(encoding="utf-8")
            self.assertIn(r"\nocite{", main_tex)
            self.assertIn("r01", main_tex)
            self.assertIn("r29", main_tex)

            # 覆盖保护：未传 --force 拒绝覆盖已有 main.tex
            rc_dup, _, err_dup = _run_cli(["html2tex", str(root / "html"), "--init-tex", "--apply"])
            self.assertEqual(rc_dup, 1)
            self.assertIn("main.tex", err_dup)

            # 紧接着 import-tex --check（及别名 tex2html）返回 0（diff == 0）
            rc_chk, out_chk, err_chk = _run_cli(["import-tex", str(root), "--check"])
            self.assertEqual(rc_chk, 0, out_chk + err_chk)
            self.assertEqual(out_chk, "")
            rc_alias, out_alias, _ = _run_cli(["tex2html", str(root / "html"), "--check"])
            self.assertEqual(rc_alias, 0)
            self.assertEqual(out_alias, "")

            # 单句编辑摘要与第 2 章 -> export-tex --apply 仅更新变更文件且重导入零差异
            untouched_p = root / "sections/01_最优估计与正交投影.tex"
            untouched_snap = untouched_p.read_bytes()
            main_md_p = root / "html/src/main.md"
            main_md_p.write_text(
                main_md_p.read_text(encoding="utf-8").replace(
                    "证明了滤波问题是无噪声调节器问题的对偶问题。",
                    "严格证明了线性滤波问题与无噪声调节器问题的对偶关系。",
                ),
                encoding="utf-8",
            )
            rc_exp, diff_out, err_exp = _run_cli(["export-tex", str(root), "--apply"])
            self.assertEqual(rc_exp, 0, err_exp)
            self.assertIn("abstract.tex", diff_out)
            self.assertEqual(untouched_p.read_bytes(), untouched_snap)
            self.assertEqual(_run_cli(["import-tex", str(root), "--check"])[0], 0)


class TestAcademicPresetAndPlainMarkdown(unittest.TestCase):
    def test_academic_md_init_and_export_tex_closed_loop(self) -> None:
        with tempfile.TemporaryDirectory(prefix="texsync_c_acad_") as tmp:
            proj = Path(tmp) / "paper"
            rc_init, _, err_init = _run_cli(["init", str(proj), "--preset", "academic-md", "--title", "滤波收敛性讲义"])
            self.assertEqual(rc_init, 0, err_init)

            rc_scaf, _, err_scaf = _run_cli(["export-tex", str(proj), "--init-tex", "--apply"])
            self.assertEqual(rc_scaf, 0, err_scaf)
            self.assertTrue((proj / "tex/main.tex").is_file())
            self.assertTrue((proj / "tex/.gitignore").is_file())
            self.assertTrue((proj / "texsync.json").is_file())
            self.assertIn("滤波收敛性讲义", (proj / "tex/main.tex").read_text(encoding="utf-8"))
            self.assertIn("demo2024", (proj / "tex/main.tex").read_text(encoding="utf-8"))

            # 双路径校验 F(TeX) == Markdown 零差异
            rc_chk1, out1, err1 = _run_cli(["import-tex", str(proj), "--check"])
            self.assertEqual(rc_chk1, 0, out1 + err1)
            rc_chk2, out2, err2 = _run_cli(["import-tex", str(proj / "tex"), "-o", str(proj), "--check"])
            self.assertEqual(rc_chk2, 0, out2 + err2)

            # 编辑正文句子后最小差异回写闭环
            md01 = proj / "src/01_正文.md"
            md01.write_text(
                md01.read_text(encoding="utf-8").replace("则误差序列依均方有界。", "则滤波误差序列依均方一致有界。"),
                encoding="utf-8",
            )
            self.assertEqual(_run_cli(["export-tex", str(proj), "--apply"])[0], 0)
            self.assertEqual(_run_cli(["import-tex", str(proj), "--check"])[0], 0)

    def test_no_bib_and_no_main_md_directory_scaffold(self) -> None:
        with tempfile.TemporaryDirectory(prefix="texsync_c_nobib_") as tmp:
            base = Path(tmp)
            src = base / "html/src"
            src.mkdir(parents=True)
            (src / "01_单章.md").write_text("<!-- title: 无文献笔记 -->\n\n# 导言 {#sec:1}\n\n仅含公式 $x_k = 0$。\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                rc = scaffold_tex_project(base / "html", apply=True)
            self.assertEqual(rc, 0)
            main_tex = (base / "main.tex").read_text(encoding="utf-8")
            self.assertNotIn(r"\nocite", main_tex)
            self.assertNotIn(r"\bibliographystyle", main_tex)
            self.assertTrue((base / "sections/01_单章.tex").is_file())


class TestBookNestedInputAndGatekeeper(unittest.TestCase):
    def _make_book_project(self, root: Path) -> dict[str, Path]:
        (root / "sections/sub").mkdir(parents=True)
        main_p = root / "main.tex"
        ch01_p = root / "sections/ch01_intro.tex"
        ch02_p = root / "sections/ch02_algorithms.tex"
        alg_p = root / "sections/sub/bpf_alg.tex"
        err_p = root / "sections/sub/error_analysis.tex"

        main_p.write_text(
            "\\documentclass[UTF8]{ctexbook}\n\\usepackage{amsmath,amsthm}\n\\newtheorem{theorem}{定理}\n"
            "\\begin{document}\n\\input{sections/ch01_intro}\n\\input{sections/ch02_algorithms}\n\\end{document}\n",
            encoding="utf-8",
        )
        ch01_p.write_text(
            "% 第一章注释\n\\chapter{绪论}[Introduction]\\label{ch:intro}\n\n"
            "本章概述非线性滤波脉络，详见第~\\ref{ch:alg}~章与算法~\\ref{alg:bpf}。\n",
            encoding="utf-8",
        )
        ch02_p.write_text(
            "\\chapter{核心算法分析}[Algorithm Analysis]\\label{ch:alg}\n\n"
            "本章给出粒子滤波流程与收敛性分析。 % 父章保留注释\n\n"
            "\\input{sections/sub/bpf_alg}\n\n"
            "\\input{sections/sub/error_analysis}\n",
            encoding="utf-8",
        )
        alg_p.write_text(
            "\\begin{algorithm}[htbp]\n\\caption{自举粒子滤波递推流程}\\label{alg:bpf}\n"
            "\\KwIn{先验粒子集 $\\{x_0^{(i)}\\}_{i=1}^N$}\n\\KwOut{后验估计 $\\hat{x}_k$}\n"
            "按似然权重重采样并推进状态\n\\end{algorithm}\n",
            encoding="utf-8",
        )
        err_p.write_text(
            "% 子文件头注释\n\\section{收敛误差界}\\label{sec:err}\n\n"
            "第一句讨论均方误差与式~\\eqref{eq:bound} 的渐近阶。 % 子文件句尾注释\n"
            "第二句给出旧版常数上界。\n\n"
            "\\begin{equation}\\label{eq:bound}\ne_N \\le C N^{-1/2}\n\\end{equation}\n",
            encoding="utf-8",
        )
        return {"ch01": ch01_p, "ch02": ch02_p, "alg": alg_p, "err": err_p}

    def test_nested_input_minimal_subfile_patch_and_zero_byte_gatekeeper(self) -> None:
        with tempfile.TemporaryDirectory(prefix="texsync_c_book_") as tmp:
            root = Path(tmp)
            paths = self._make_book_project(root)

            # 1. 导入含 \chapter + 纯 algorithm 子文件 + 正文嵌套 \input 子文件的 book 工程
            rc_imp, _, err_imp = _run_cli(["import-tex", str(root), "--apply"])
            self.assertEqual(rc_imp, 0, err_imp)
            self.assertEqual(_run_cli(["import-tex", str(root), "--check"])[0], 0)

            manifest = json.loads((root / "html/texsync.json").read_text(encoding="utf-8"))
            md_by_tex = {p["tex"]: root / "html" / p["md"] for p in manifest["pairs"]}
            ch01_md_p = md_by_tex["sections/ch01_intro.tex"]
            ch02_md_p = md_by_tex["sections/ch02_algorithms.tex"]
            ch02_orig_md = ch02_md_p.read_text(encoding="utf-8")
            self.assertIn("<!--tex-file: sections/sub/error_analysis.tex-->", ch02_orig_md)
            self.assertIn('<figure class="alg"', ch02_orig_md)
            self.assertTrue((root / "html/src/algs/bpf.tex").is_file())

            # 2. 仅编辑嵌套子文件块内单句 -> export-tex --apply 仅改 error_analysis.tex 且保留父文件 \input 与副标题
            snap_before = {k: p.read_bytes() for k, p in paths.items()}
            ch02_edited = ch02_orig_md.replace("第二句给出旧版常数上界。", "第二句已收紧为显式常数上界。")
            ch02_md_p.write_text(ch02_edited, encoding="utf-8")

            rc_exp, _, err_exp = _run_cli(["export-tex", str(root), "--apply"])
            self.assertEqual(rc_exp, 0, err_exp)
            self.assertEqual(paths["ch01"].read_bytes(), snap_before["ch01"])
            self.assertEqual(paths["ch02"].read_bytes(), snap_before["ch02"])
            self.assertEqual(paths["alg"].read_bytes(), snap_before["alg"])
            err_after = paths["err"].read_text(encoding="utf-8")
            self.assertIn("% 子文件头注释\n", err_after)
            self.assertIn("式~\\eqref{eq:bound} 的渐近阶。 % 子文件句尾注释", err_after)
            self.assertIn("第二句已收紧为显式常数上界。", err_after)
            self.assertEqual(_run_cli(["import-tex", str(root), "--check"])[0], 0)

            # 3. 门禁场景 A：ch01 合法修改 + ch02 篡改 algorithm 浮动体 -> 返回 1 且全部文件 0 字节写入
            snap_clean = {k: p.read_bytes() for k, p in paths.items()}
            ch01_orig_md = ch01_md_p.read_text(encoding="utf-8")
            ch01_md_p.write_text(ch01_orig_md.replace("非线性滤波脉络", "顺序蒙特卡洛脉络"), encoding="utf-8")
            ch02_md_p.write_text(ch02_edited.replace("自举粒子滤波递推流程", "篡改后的算法标题"), encoding="utf-8")
            rc_bad1, _, err_bad1 = _run_cli(["export-tex", str(root), "--apply"])
            self.assertEqual(rc_bad1, 1)
            self.assertIn("需人工处理", err_bad1)
            self.assertEqual({k: p.read_bytes() for k, p in paths.items()}, snap_clean)

            # 4. 门禁场景 B：删除 <!--tex-file: ...--> 定界注释 -> 返回 1 且全部文件 0 字节写入
            ch02_md_p.write_text(ch02_edited.replace("<!--tex-file: sections/sub/error_analysis.tex-->\n\n", ""), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err_b2:
                rc_bad2 = execute_export(root / "html", apply=True)
            self.assertEqual(rc_bad2, 1)
            self.assertIn("需人工处理", err_b2.getvalue())
            self.assertEqual({k: p.read_bytes() for k, p in paths.items()}, snap_clean)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(execute_import(root, root / "html", check=True), 1)


class TestCliTplLineBudgets(unittest.TestCase):
    def test_line_budgets(self) -> None:
        cli_p = Path(cli.__file__).resolve()
        scaf_p = Path(sys.modules[scaffold_tex_project.__module__].__file__).resolve()
        this_p = Path(__file__).resolve()
        self.assertLessEqual(len(cli_p.read_text(encoding="utf-8").splitlines()), 180)
        self.assertLessEqual(len(scaf_p.read_text(encoding="utf-8").splitlines()), 200)
        self.assertLessEqual(len(this_p.read_text(encoding="utf-8").splitlines()), 280)


if __name__ == "__main__":
    unittest.main()
