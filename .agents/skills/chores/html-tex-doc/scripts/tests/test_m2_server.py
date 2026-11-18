#!/usr/bin/env python3
"""M2 多工程服务与路由测试（可直接并入 scripts/tests/test_htd.py 或独立运行）。"""
from __future__ import annotations

import http.client
import json
import os
import shutil
import tempfile
import threading
import unittest
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from unittest.mock import patch
from urllib.parse import quote

from htd.cli import main as cli_main
from htd.server.http import make_library_server, make_single_server
from htd.server.project import decode_paper_id, encode_paper_id, init_project

HAS_TEX = bool(shutil.which("xelatex") and shutil.which("dvisvgm"))


def _seed_md_paper(paper_dir: Path, title: str, body: str) -> None:
    src = paper_dir / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "01_正文.md").write_text(f"<!-- title: {title} -->\n\n# 第一章 {{#sec:1}}\n\n{body}\n", encoding="utf-8")


@unittest.skipUnless(HAS_TEX, "需要 xelatex 与 dvisvgm")
class MultiPaperServer(unittest.TestCase):
    def setUp(self) -> None:
        self._old_math = os.environ.get("HTD_MATH")
        os.environ["HTD_MATH"] = "browser"
        self.tmp = tempfile.TemporaryDirectory()
        self.lib_root = Path(self.tmp.name) / "论文集"
        _seed_md_paper(self.lib_root / "非线性滤波" / "html", "联合优化非线性滤波", "初始滤波段落 AlphaUnique。")
        _seed_md_paper(self.lib_root / "paper-b", "粒子退化分析", "初始粒子段落 BetaUnique。")
        self.srv = make_library_server(self.lib_root, host="127.0.0.1", port=0)
        self.port = self.srv.server_address[1]
        self.thread = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.srv.shutdown()
        self.srv.server_close()
        self.thread.join(timeout=2.0)
        self.tmp.cleanup()
        if self._old_math is None:
            os.environ.pop("HTD_MATH", None)
        else:
            os.environ["HTD_MATH"] = self._old_math

    def _req(self, method: str, path: str, body: object | None = None) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15.0)
        try:
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
            headers = {"Content-Type": "application/json; charset=utf-8"} if payload is not None else {}
            conn.request(method, path, body=payload, headers=headers)
            resp = conn.getresponse()
            hdrs = {k.lower(): v for k, v in resp.getheaders()}
            return resp.status, hdrs, resp.read()
        finally:
            conn.close()

    def _json(self, method: str, path: str, body: object | None = None) -> tuple[int, dict[str, object]]:
        st, _, raw = self._req(method, path, body)
        return st, json.loads(raw.decode("utf-8"))

    def test_slug_codec_and_shell_routes(self) -> None:
        for pid in ("paper-b", "非线性滤波/html", "draft~v1/sub"):
            self.assertEqual(decode_paper_id(encode_paper_id(pid)), pid)
        for bad in ("", "..~secret", "~abs", "foo~", "a%2Fb", "a%5Cb", "a%00b"):
            self.assertIsNone(decode_paper_id(bad))

        for path, ctype in (("/", "text/html"), ("/__shell.css", "text/css"), ("/__shell.js", "javascript")):
            st, hdrs, raw = self._req("GET", path)
            self.assertEqual(st, 200)
            self.assertIn(ctype, hdrs["content-type"])
            self.assertTrue(len(raw) > 0)

        with patch("htd.cli.run_library_server", return_value=0) as m_lib:
            with patch("sys.argv", ["htd", "serve", "--library"]):
                self.assertEqual(cli_main(), 0)
            self.assertTrue(str(m_lib.call_args.kwargs["library_root"]).endswith("co-work 资产/tex-论文/论文集"))
            with patch("sys.argv", ["htd", "serve", "--library", str(self.lib_root), "--port", "19999"]):
                self.assertEqual(cli_main(), 0)
            self.assertEqual(m_lib.call_args.kwargs["library_root"], self.lib_root.resolve())
            self.assertEqual(m_lib.call_args.kwargs["port"], 19999)

    def test_lazy_start_redirect_and_clean_disk_index(self) -> None:
        st, data = self._json("GET", "/__api/papers")
        self.assertEqual(st, 200)
        self.assertEqual(data["library"], "论文集")
        by_id = {p["id"]: p for p in data["papers"]}  # type: ignore[index]
        self.assertEqual(set(by_id), {"paper-b", "非线性滤波/html"})
        for p in by_id.values():
            self.assertFalse(p["alive"])
        self.assertFalse((self.lib_root / "paper-b" / "outputs" / "site" / "index.html").exists())

        slug_a = by_id["非线性滤波/html"]["slug"]
        st_redir, hdrs, _ = self._req("GET", f"/p/{slug_a}")
        self.assertEqual(st_redir, 302)
        self.assertEqual(hdrs["location"], f"/p/{slug_a}/")
        # 仅 302 重定向尚未访问带斜杠主页，不应启动构建线程
        _, data_mid = self._json("GET", "/__api/papers")
        self.assertFalse({p["id"]: p for p in data_mid["papers"]}["非线性滤波/html"]["alive"])  # type: ignore[index]

        st_page, _, raw_page = self._req("GET", f"/p/{slug_a}/")
        self.assertEqual(st_page, 200)
        page_html = raw_page.decode("utf-8")
        expected_boot = (
            f'<script>window.__HTML_TEX_LIVE__ = true; window.__HTD_BASE__ = "/p/{slug_a}/"; '
            f'window.__HTD_PAPER__ = "非线性滤波/html";</script>'
        )
        self.assertIn(expected_boot, page_html)
        self.assertIn(f'<script defer src="/p/{slug_a}/__editor.js"></script>\n</head>', page_html)
        self.assertLess(page_html.index(expected_boot), page_html.index('src="reader.js"'))

        disk_html = (self.lib_root / "非线性滤波" / "html" / "outputs" / "site" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("__HTML_TEX_LIVE__", disk_html)
        self.assertNotIn("__HTD_BASE__", disk_html)
        self.assertNotIn("__editor.js", disk_html)

        # 未访问的 paper-b 仍保持 alive == False
        _, data_after = self._json("GET", "/__api/papers")
        by_after = {p["id"]: p for p in data_after["papers"]}  # type: ignore[index]
        self.assertTrue(by_after["非线性滤波/html"]["alive"])
        self.assertFalse(by_after["paper-b"]["alive"])

        # 静态产物可正常获取且越界路径被拦截
        st_css, _, css_raw = self._req("GET", f"/p/{slug_a}/style.css")
        self.assertEqual(st_css, 200)
        self.assertTrue(len(css_raw) > 100)
        st_bad, _, _ = self._req("GET", f"/p/{slug_a}/..%2F..%2Fsrc%2F01_%E6%AD%A3%E6%96%87.md")
        self.assertIn(st_bad, (403, 404))

        # 删除目录后动态清理并停止对应工程线程
        proj_a = self.srv.library.projects["非线性滤波/html"]  # type: ignore[union-attr]
        shutil.rmtree(self.lib_root / "非线性滤波")
        _, data_del = self._json("GET", "/__api/papers")
        self.assertEqual([p["id"] for p in data_del["papers"]], ["paper-b"])  # type: ignore[index]
        self.assertFalse(proj_a.alive)

    def test_create_paper_and_immediate_rw(self) -> None:
        for bad_name in ("", "../evil", "sub/dir", ".hidden", "src"):
            st_bad, _ = self._json("POST", "/__api/papers", {"name": bad_name})
            self.assertEqual(st_bad, 400)

        st, res = self._json("POST", "/__api/papers", {"name": "new-kalman", "title": "新建卡尔曼专题"})
        self.assertEqual(st, 201, res)
        paper = res["paper"]  # type: ignore[index]
        self.assertTrue(paper["alive"])
        self.assertEqual(paper["title"], "新建卡尔曼专题")
        slug = paper["slug"]

        st_dup, _ = self._json("POST", "/__api/papers", {"name": "new-kalman"})
        self.assertEqual(st_dup, 409)

        st_f, files_res = self._json("GET", f"/p/{slug}/__api/files")
        self.assertEqual(st_f, 200)
        paths = [f["path"] for f in files_res["files"]]  # type: ignore[index]
        target = "01_正文.md" if "01_正文.md" in paths else paths[0]

        st_r, file_data = self._json("GET", f"/p/{slug}/__api/file?path={quote(target)}")
        self.assertEqual(st_r, 200)
        updated = str(file_data["content"]) + "\n新增测试行 NewKalmanToken。\n"
        st_w, put_res = self._json(
            "PUT",
            f"/p/{slug}/__api/file",
            {"path": target, "content": updated, "base_mtime_ns": file_data["mtime_ns"]},
        )
        self.assertEqual(st_w, 200)
        self.assertTrue(put_res["ok"])

        # 验证 init_project 对 main.md 前置块 title: 文档标题 的替换支持
        fake_tpl = Path(self.tmp.name) / "fake_tpl"
        fake_tpl.mkdir()
        (fake_tpl / "main.md").write_text("---\ntitle: 文档标题\nmacros: macros.tex\n---\n", encoding="utf-8")
        probe = Path(self.tmp.name) / "main_title_probe"
        with patch("htd.server.project.TEMPLATE_ACADEMIC", fake_tpl):
            init_project(probe, title="前置块自定义标题", preset="academic-md")
        self.assertIn("title: 前置块自定义标题", (probe / "src" / "main.md").read_text(encoding="utf-8"))

    def test_concurrent_edit_isolation_and_error_containment(self) -> None:
        slug_a = encode_paper_id("非线性滤波/html")
        slug_b = encode_paper_id("paper-b")
        for s in (slug_a, slug_b):
            self.assertEqual(self._req("GET", f"/p/{s}/")[0], 200)

        _, live_a0 = self._json("GET", f"/p/{slug_a}/__live?v=-1")
        _, live_b0 = self._json("GET", f"/p/{slug_b}/__live?v=-1")
        va0, vb0 = int(live_a0["v"]), int(live_b0["v"])  # type: ignore[arg-type]

        # 并发向两篇论文写入：A 故意写入未闭合 ::: 触发 Markdown 报错，B 写入合法更新
        bad_a = "<!-- title: 联合优化非线性滤波 -->\n\n# 第一章 {#sec:1}\n\nAlphaEditToken\n\n::: 定理 {#thm:broken}\n未闭合块\n"
        good_b = "<!-- title: 粒子退化分析 -->\n\n# 第一章 {#sec:1}\n\nBetaEditToken 正常刷新内容。\n"
        results: dict[str, int] = {}

        def put_doc(key: str, slug: str, txt: str) -> None:
            st, _ = self._json("PUT", f"/p/{slug}/__api/file", {"path": "01_正文.md", "content": txt, "force": True})
            results[key] = st

        t1 = threading.Thread(target=put_doc, args=("a", slug_a, bad_a))
        t2 = threading.Thread(target=put_doc, args=("b", slug_b, good_b))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assertEqual(results, {"a": 200, "b": 200})

        _, live_a1 = self._json("GET", f"/p/{slug_a}/__live?v={va0}")
        _, live_b1 = self._json("GET", f"/p/{slug_b}/__live?v={vb0}")
        self.assertTrue(str(live_a1["err"]), "A 应报告未闭合块错误")
        self.assertEqual(live_b1["err"], "", "B 不受 A 报错影响")

        _, _, raw_b = self._req("GET", f"/p/{slug_b}/__raw")
        self.assertIn("BetaEditToken", raw_b.decode("utf-8"))

        # 搜索与 WAL 历史严格隔离
        _, srch_a = self._json("GET", f"/p/{slug_a}/__api/search?q=BetaEditToken")
        _, srch_b = self._json("GET", f"/p/{slug_b}/__api/search?q=BetaEditToken")
        self.assertEqual(len(srch_a["hits"]), 0)  # type: ignore[arg-type]
        self.assertEqual(len(srch_b["hits"]), 1)  # type: ignore[arg-type]

        _, hist_a = self._json("GET", f"/p/{slug_a}/__api/history?path={quote('01_正文.md')}")
        _, hist_b = self._json("GET", f"/p/{slug_b}/__api/history?path={quote('01_正文.md')}")
        self.assertEqual(len(hist_a["ops"]), 1)  # type: ignore[arg-type]
        self.assertEqual(len(hist_b["ops"]), 1)  # type: ignore[arg-type]
        op_b = hist_b["ops"][0]["id"]  # type: ignore[index]
        st_rb, rb_res = self._json("POST", f"/p/{slug_b}/__api/rollback", {"path": "01_正文.md", "id": op_b})
        self.assertEqual(st_rb, 200)
        self.assertIn("BetaUnique", str(rb_res["content"]))

    def test_single_server_backward_compat(self) -> None:
        single_dir = Path(self.tmp.name) / "single"
        _seed_md_paper(single_dir, "单工程测试", "SingleModeBody")
        srv1 = make_single_server(single_dir / "src", single_dir / "build", single_dir / "out", port=0)
        t = threading.Thread(target=srv1.serve_forever, daemon=True)
        t.start()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", srv1.server_address[1], timeout=10.0)
            conn.request("GET", "/")
            page = conn.getresponse().read().decode("utf-8")
            conn.close()
            self.assertIn('window.__HTD_BASE__ = "/"; window.__HTD_PAPER__ = "";', page)
            self.assertIn('<script defer src="/__editor.js"></script>', page)
            self.assertNotIn("__HTML_TEX_LIVE__", (single_dir / "out" / "index.html").read_text(encoding="utf-8"))
        finally:
            srv1.shutdown()
            srv1.server_close()
            t.join(timeout=2.0)


if __name__ == "__main__":
    unittest.main()
