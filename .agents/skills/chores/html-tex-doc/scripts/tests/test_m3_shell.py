#!/usr/bin/env python3
"""M3 外壳页、设计变量、接口前缀化与存储隔离单元回归测试。"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SCRIPTS = _HERE / "scripts" if (_HERE / "scripts" / "htd").is_dir() else _HERE.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from htd import assets  # noqa: E402
from htd.paths import ASSETS_DIR  # noqa: E402


class ShellAssetsAndIsolation(unittest.TestCase):
    LITERAL = re.compile(
        r"#[0-9a-fA-F]{3,8}\b|rgba?\(|border-radius:[^;]*\dpx|z-index:\s*\d|\"[A-Z][^\"]* (?:CJK|Mono|Sans|Serif)[^\"]*\""
    )
    HARDCODED_FETCH = re.compile(r"""fetch\s*\(\s*["'`]/__|["'`]/__(?:api|raw|live)\b""")
    LONG_OK = {"70_workbench.js"}

    def test_shell_bundles_and_render_html(self):
        shell_css = assets.bundle("shell.css")
        tokens_css = (ASSETS_DIR / "css" / "00_tokens.css").read_text(encoding="utf-8")
        comp_css = (ASSETS_DIR / "css" / "08_components.css").read_text(encoding="utf-8")
        self.assertTrue(shell_css.startswith(tokens_css))
        self.assertIn(comp_css, shell_css)
        self.assertIn(".sh-rail", shell_css)
        self.assertIn(".sh-frame", shell_css)

        # 单篇论文 style.css 不混入外壳私有样式
        style_css = assets.bundle("style.css")
        self.assertNotIn(".sh-rail", style_css)
        self.assertNotIn(".sh-frame", style_css)

        shell_js = assets.bundle("shell.js")
        core_js = (ASSETS_DIR / "js" / "core.js").read_text(encoding="utf-8")
        self.assertTrue(shell_js.startswith(core_js))
        self.assertIn("MAX_ALIVE = 3", shell_js)

        html_doc = assets.render_shell_html("测试<工作区>")
        self.assertIn("<title>测试&lt;工作区&gt;</title>", html_doc)
        self.assertIn('href="/__shell.css"', html_doc)
        self.assertIn('defer src="/__shell.js"', html_doc)
        self.assertIn('id="sh-app"', html_doc)
        self.assertIn('localStorage.getItem("reader.theme")', html_doc)

    def test_literals_live_only_in_tokens_including_shell(self):
        css_files = {p for n in ("style.css", "shell.css") for p in assets.part_files(n)}
        for f in sorted(css_files):
            if f.name == "00_tokens.css":
                continue
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                self.assertIsNone(
                    self.LITERAL.search(line),
                    f"{f.name}:{i} 出现了应放进 00_tokens.css 的字面量：{line.strip()[:80]}",
                )

    def test_shell_frame_uses_visibility_not_display_none(self):
        shell_only_css = (ASSETS_DIR / "css" / "shell" / "60_shell.css").read_text(encoding="utf-8")
        self.assertIn("visibility: hidden", shell_only_css)
        self.assertIn("visibility: visible", shell_only_css)
        self.assertIn("transition: none", shell_only_css)
        self.assertIn(".sh-toggle", shell_only_css)
        self.assertIn(".sh-rail.is-collapsed", shell_only_css)
        self.assertNotIn("grid-template-columns", shell_only_css)
        # 确保 .sh-frame 与 .sh-rail.is-collapsed 绝不使用 display: none
        for sel in (r"\.sh-frame", r"\.sh-rail\.is-collapsed"):
            m = re.search(sel + r"\s*\{([^}]*)\}", shell_only_css)
            self.assertIsNotNone(m, sel)
            self.assertNotIn("display: none", m.group(1))
        ed_css = (ASSETS_DIR / "css" / "50_editor.css").read_text(encoding="utf-8")
        self.assertIn('html[data-in-shell="1"][data-split="1"] .ed-topbar', ed_css)

    def test_source_files_stay_within_line_limits(self):
        bundles = ("style.css", "reader.js", "editor.js", "shell.css", "shell.js")
        files = {p for n in bundles for p in assets.part_files(n)}
        files.update((SCRIPTS / "htd").rglob("*.py"))
        for f in sorted(files):
            n = len(f.read_text(encoding="utf-8").splitlines())
            if f.name == "00_shell.js":
                self.assertLessEqual(n, 280, f"00_shell.js 超出 280 行限制：{n} 行")
            elif f.name not in self.LONG_OK:
                self.assertLessEqual(n, 300, f"{f} 超出 300 行限制：{n} 行")

    def test_ui_classes_used_across_all_bundles_are_defined(self):
        css = (ASSETS_DIR / "css" / "08_components.css").read_text(encoding="utf-8")
        defined = set(re.findall(r"\.(ui-[a-z-]+)", css))
        sources = [p for n in ("reader.js", "editor.js", "shell.js") for p in assets.part_files(n)]
        sources.append(SCRIPTS / "htd" / "toc.py")
        used = {c for p in sources for c in re.findall(r"\b(ui-[a-z]+(?:--[a-z]+)?)\b", p.read_text(encoding="utf-8"))}
        self.assertTrue(used)
        self.assertEqual(used - defined, set(), f"存在未在 08_components.css 定义的 ui-* 类：{used - defined}")

    def test_editor_js_has_no_hardcoded_root_api_paths(self):
        for f in assets.part_files("editor.js"):
            text = f.read_text(encoding="utf-8")
            m = self.HARDCODED_FETCH.search(text)
            self.assertIsNone(m, f"{f.name} 仍残留硬编码根路径接口调用：{m.group(0) if m else ''}")

    @unittest.skipUnless(shutil.which("node"), "需要 node 运行前端隔离断言")
    def test_core_api_prefix_and_store_isolation(self):
        core_path = ASSETS_DIR / "js" / "core.js"
        script = f"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync({json.dumps(str(core_path))}, "utf8");
function makeEnv(base, paper, bag) {{
  const ls = {{
    getItem: (k) => (k in bag ? bag[k] : null),
    setItem: (k, v) => {{ bag[k] = String(v); }},
    removeItem: (k) => {{ delete bag[k]; }},
  }};
  const win = {{ __HTD_BASE__: base, __HTD_PAPER__: paper, localStorage: ls }};
  win.window = win;
  vm.runInNewContext(code, win);
  return win.HTD;
}}
const bag = {{}};
const single = makeEnv("/", "", bag);
single.store.set("reader.theme", "dark");
single.store.set("editor.lastFile", "01.md");

const libA = makeEnv("/p/p1/", "非线性滤波/html", bag);
const libB = makeEnv("/p/p2/", "kalman-note", bag);
libA.store.set("editor.lastFile", "a.md");
libB.store.set("editor.lastFile", "b.md");
libA.store.set("editor.splitOpen", "1");
libB.store.set("editor.autoSave", "0");

console.log(JSON.stringify({{
  singleRaw: single.api("__raw"),
  singleSlash: single.api("/__api/files"),
  libARaw: libA.api("__raw"),
  libASlash: libA.api("/__api/file?path=a.md"),
  themeInA: libA.store.get("reader.theme"),
  autoSaveInA: libA.store.get("editor.autoSave"),
  singleLast: single.store.get("editor.lastFile"),
  aLast: libA.store.get("editor.lastFile"),
  bLast: libB.store.get("editor.lastFile"),
  bSplit: libB.store.get("editor.splitOpen"),
  keys: Object.keys(bag).sort(),
}}));
"""
        proc = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
        out = json.loads(proc.stdout)
        self.assertEqual(out["singleRaw"], "/__raw")
        self.assertEqual(out["singleSlash"], "/__api/files")
        self.assertEqual(out["libARaw"], "/p/p1/__raw")
        self.assertEqual(out["libASlash"], "/p/p1/__api/file?path=a.md")
        self.assertEqual(out["themeInA"], "dark")
        self.assertEqual(out["autoSaveInA"], "0")
        self.assertEqual(out["singleLast"], "01.md")
        self.assertEqual(out["aLast"], "a.md")
        self.assertEqual(out["bLast"], "b.md")
        self.assertIsNone(out["bSplit"])
        self.assertIn("htd:非线性滤波/html:editor.lastFile", out["keys"])
        self.assertIn("htd:kalman-note:editor.lastFile", out["keys"])


if __name__ == "__main__":
    unittest.main()
