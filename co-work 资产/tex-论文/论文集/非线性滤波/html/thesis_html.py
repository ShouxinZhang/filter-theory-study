#!/usr/bin/env python3
"""论文 HTML 副本：src/*.md → outputs/site/index.html（经 html-tex-doc 构建器编号与出图）。

    python3 thesis_html.py build          # 构建一次
    python3 thesis_html.py serve          # 监听 src/，保存即局部刷新 http://127.0.0.1:18767

Markdown 约定见 README.md。本副本独立于上级目录的 TeX 论文，互不同步。
"""
from __future__ import annotations

import argparse
import contextlib
import html
import importlib.util
import io
import json
import re
import shutil
import sys
import threading
import time
import unicodedata
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
SRC, BUILD, SITE = HERE / "src", HERE / "build", HERE / "outputs" / "site"
GEN = BUILD / "gen"

MATH = re.compile(r"(?<![\\$])\$(?!\$)(.+?)(?<![\\$])\$", re.S)
FENCE = re.compile(r"^\$\$\s*(?:\{#([^}]+)\})?\s*$")
HEAD = re.compile(r"^(#{1,3})\s+(.*?)(?:\s*\{#([^}]+)\})?\s*$")
BOX_OPEN = re.compile(r"^:::\s*(\S+)(?:\s+\{#([^}]+)\})?\s*(.*)$")
ITEM = re.compile(r"^(\d+\.|-)\s+")
RAW = re.compile(r"^<(figure|table|header|div|nav|section|ol|ul|img|p|h[1-6]|blockquote|details|!--)")


def load_builder():
    for p in HERE.parents:
        f = p / ".agents/skills/chores/html-tex-doc/scripts/html_tex_doc.py"
        if f.exists():
            spec = importlib.util.spec_from_file_location("html_tex_doc", f)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["html_tex_doc"] = mod
            spec.loader.exec_module(mod)
            return mod
    sys.exit("找不到 .agents/skills/chores/html-tex-doc/scripts/html_tex_doc.py")


# ---------------------------------------------------------------- 参考文献
def _clean(v: str) -> str:
    v = re.sub(r"""\\(["'`^~])\{?(\w)\}?""", lambda m: unicodedata.normalize(
        "NFC", m.group(2) + {'"': "\u0308", "'": "\u0301", "`": "\u0300", "^": "\u0302", "~": "\u0303"}[m.group(1)]), v)
    v = v.replace(r"\&", "&").replace("--", "–").replace("{", "").replace("}", "").replace("~", " ")
    return html.escape(" ".join(v.split()), quote=False)


def parse_bib(text: str) -> dict[str, dict[str, str]]:
    text = re.sub(r"^\s*%.*$", "", text, flags=re.M)
    out: dict[str, dict[str, str]] = {}
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        i, depth = m.end(), 1
        j = i
        while depth and j < len(text):
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        body, fields, pos = text[i:j - 1], {}, 0
        while fm := re.compile(r"\s*,?\s*(\w+)\s*=\s*").match(body, pos):
            k = fm.end()
            if body[k:k + 1] == "{":
                d, e = 1, k + 1
                while d and e < len(body):
                    d += {"{": 1, "}": -1}.get(body[e], 0)
                    e += 1
                val = body[k + 1:e - 1]
            elif body[k:k + 1] == '"':
                e = body.index('"', k + 1) + 1
                val = body[k + 1:e - 1]
            else:
                e = body.find(",", k)
                e = len(body) if e < 0 else e
                val = body[k:e]
            fields[fm.group(1).lower()] = val
            pos = e
        out[m.group(2)] = fields
    return out


def fmt_ref(f: dict[str, str]) -> str:
    names = []
    for a in re.split(r"\s+and\s+", f.get("author", "")):
        if "," in a and not a.strip().startswith("{"):
            last, first = a.split(",", 1)
            a = f"{first.strip()} {last.strip()}"
        if a.strip():
            names.append(_clean(a))
    who = ", ".join(names[:3]) + (" et al." if len(names) > 3 else "")
    venue = next((f[k] for k in ("journal", "booktitle", "publisher", "school", "howpublished") if f.get(k)), "")
    bits = [who, _clean(f.get("title", "")), f"<em>{_clean(venue)}</em>" if venue else "", _clean(f.get("year", ""))]
    return ". ".join(b for b in bits if b) + "."


# ---------------------------------------------------------------- Markdown → doc.html
def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Conv:
    def __init__(self, bib: dict[str, dict[str, str]]):
        self.bib, self.cites, self.errors, self.auto = bib, [], [], 0
        self.sec = [0, 0, 0]                      # 与构建器的 h2/h3 编号同步，用于给 ### 小节编号
        self.sub: dict[str, tuple[str, str]] = {}  # ### 小节标签 → (编号, 锚点)

    def cite(self, m: re.Match[str]) -> str:
        out = []
        for k in re.split(r"\s*[,;]\s*@?", m.group(1).strip()):
            if k not in self.bib:
                self.errors.append(f"未知文献键：{k}")
                continue
            if k not in self.cites:
                self.cites.append(k)
            out.append(f'<a class="cite" href="#ref-{k}">{self.cites.index(k) + 1}</a>')
        return '<sup class="cites">[' + ",".join(out) + "]</sup>"

    def inline(self, s: str) -> str:
        stash: list[str] = []

        def keep(m: re.Match[str]) -> str:
            stash.append(r"\(" + esc(m.group(1)) + r"\)")
            return f"\x00{len(stash) - 1}\x00"

        s = MATH.sub(keep, s).replace(r"\$", "$")
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s, flags=re.S)
        s = re.sub(r"\[@([^\]]+)\]", self.cite, s)
        return re.sub("\x00(\\d+)\x00", lambda m: stash[int(m.group(1))], s)

    def eq(self, label: str | None, body: str) -> str:
        lab = f' data-label="{label}"' if label else ""
        return f'<div class="eq"{lab}>\n\\[ {esc(body)} \\]\n</div>'

    def item(self, x: str) -> str:
        """列表项：允许内含 $$ 行间公式。"""
        out, buf, lines, i = [], [], x.split("\n"), 0
        while i < len(lines):
            if m := FENCE.match(lines[i]):
                j = i + 1
                while j < len(lines) and lines[j].strip() != "$$":
                    j += 1
                out += [self.inline("\n".join(buf)), self.eq(m.group(1), "\n".join(lines[i + 1:j]))]
                buf, i = [], j + 1
            else:
                buf.append(lines[i])
                i += 1
        return "".join(out) + self.inline("\n".join(buf))

    def link_subsections(self, doc: str) -> str:
        def fn(m: re.Match[str]) -> str:
            if m.group(1) not in self.sub:
                return m.group(0)
            num, anchor = self.sub[m.group(1)]
            return f'<a class="xref" href="#{anchor}">{num if m.group(2) else f"第 {num} 节"}</a>'
        return re.sub(r"\{@([\w:.-]+)(\|n)?\}", fn, doc)

    def refs_html(self) -> str:
        return '<ol class="refs">' + "".join(
            f'<li id="ref-{k}">{fmt_ref(self.bib[k])}</li>' for k in self.cites) + "</ol>"

    def convert(self, text: str, name: str) -> str:
        out: list[str] = []
        para: list[str] = []
        stack: list[str] = []
        prefix = ""
        lines = text.split("\n")
        i = 0

        def flush() -> None:
            nonlocal prefix
            if para:
                out.append(f"<p>{prefix}{self.inline(chr(10).join(para))}</p>")
                prefix = ""
                para.clear()

        while i < len(lines):
            line = lines[i].rstrip()
            if m := FENCE.match(line):
                flush()
                j = i + 1
                while j < len(lines) and lines[j].strip() != "$$":
                    j += 1
                if j == len(lines):
                    self.errors.append(f"{name}:{i + 1} 行间公式 $$ 未闭合")
                out.append(self.eq(m.group(1), "\n".join(lines[i + 1:j])))
                i = j + 1
                continue
            if not line.strip():
                flush()
            elif line.strip() == ":::":
                flush()
                if not stack:
                    self.errors.append(f"{name}:{i + 1} 多余的 :::")
                elif stack.pop() == "proof":
                    out.append('<p class="qed">∎</p>')
                out.append("</div>")
            elif m := BOX_OPEN.match(line):
                flush()
                kind, label, title = m.group(1), m.group(2), m.group(3).strip()
                if kind == "证明":
                    stack.append("proof")
                    out.append('<div class="proof">')
                    prefix = f"<em>{self.inline(title) if title else '证明'}.</em> "
                else:
                    if not label:
                        self.auto += 1
                        label = f"thm:auto-{self.auto}"
                    stack.append("thm")
                    t = f' data-title="{html.escape(title)}"' if title else ""
                    out.append(f'<div class="thm" data-kind="{kind}" data-label="{label}"{t}>')
            elif (m := HEAD.match(line)) and not para:
                lv = len(m.group(1))
                self.sec = self.sec[:lv - 1] + [self.sec[lv - 1] + 1] + [0] * (3 - lv)
                if lv == 3:
                    num = ".".join(map(str, self.sec))
                    anchor = re.sub(r"[^\w-]", "-", m.group(3) or f"sub-{num}")
                    if m.group(3):
                        self.sub[m.group(3)] = (num, anchor)
                    out.append(f'<h4 id="{anchor}"><span class="secnum">{num}</span>{self.inline(m.group(2))}</h4>')
                else:
                    lab = f' data-label="{m.group(3)}"' if m.group(3) else ""
                    out.append(f"<h{lv + 1}{lab}>{self.inline(m.group(2))}</h{lv + 1}>")
            elif not para and (RAW.match(line) or ITEM.match(line)):
                j = i
                while j < len(lines) and lines[j].strip():
                    j += 1
                block = [l.rstrip() for l in lines[i:j]]
                if RAW.match(line):
                    out.append(self.inline("\n".join(block)))
                else:
                    items: list[str] = []
                    for l in block:
                        if ITEM.match(l):
                            items.append(ITEM.sub("", l, 1))
                        else:
                            items[-1] += "\n" + l.strip()
                    tag = "ul" if line.startswith("-") else "ol"
                    out.append(f"<{tag}>" + "".join(f"<li>{self.item(x)}</li>" for x in items) + f"</{tag}>")
                i = j
                continue
            else:
                para.append(line)
            i += 1
        flush()
        if stack:
            self.errors.append(f"{name} 末尾有未闭合的 ::: 块")
            out.extend("</div>" for _ in stack)
        return "\n".join(out)


B = None


def build(force: bool = False) -> str:
    """返回错误文本；成功时返回空串。"""
    global B
    B = B or load_builder()
    bib_file = SRC / "refs.bib"
    conv = Conv(parse_bib(bib_file.read_text(encoding="utf-8")) if bib_file.exists() else {})
    parts = [conv.convert(f.read_text(encoding="utf-8"), f.name) for f in sorted(SRC.glob("*.md"))]
    doc = conv.link_subsections("\n".join(parts)).replace("<!--REFS-->", conv.refs_html())
    if conv.errors:
        return "Markdown 错误：\n- " + "\n- ".join(conv.errors)

    GEN.mkdir(parents=True, exist_ok=True)
    for link in GEN.iterdir():
        if link.is_symlink() and not link.exists():
            link.unlink()
    for p in SRC.iterdir():
        link = GEN / p.name
        if p.suffix != ".md" and not link.exists():
            link.symlink_to(p.resolve())
    gen_doc = GEN / "doc.html"
    if not gen_doc.exists() or gen_doc.read_text(encoding="utf-8") != doc:
        gen_doc.write_text(doc, encoding="utf-8")

    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        rc = B.cmd_build(SimpleNamespace(dir=str(HERE), src=str(GEN), build_dir=str(BUILD), out=str(SITE), force=force))
    if rc:
        return err.getvalue() or f"构建失败（退出码 {rc}）"
    for f in (SRC / "figs").glob("*") if (SRC / "figs").exists() else []:
        dst = SITE / "figs" / f.name
        if not dst.exists() or dst.stat().st_mtime < f.stat().st_mtime:
            dst.parent.mkdir(exist_ok=True)
            shutil.copy2(f, dst)
    return ""


# ---------------------------------------------------------------- 实时预览
LIVE_JS = r"""
(() => {
  let v = -1, raw = [], nodes = [], end = null, bar = null, ok = false;
  const parse = t => Array.from(new DOMParser().parseFromString(t, "text/html").body.children).map(e => e.outerHTML);
  const getRaw = async () => parse(await (await fetch("/__raw", {cache: "no-store"})).text());
  const isToc = h => h.startsWith('<nav class="toc"');
  function banner(msg) {
    if (!bar) { bar = document.createElement("pre"); bar.className = "live-err"; document.body.appendChild(bar); }
    bar.textContent = msg; bar.style.display = msg ? "block" : "none";
  }
  function make(list) { const t = document.createElement("template"); t.innerHTML = list.join(""); return Array.from(t.content.children); }
  async function patch() {
    const next = await getRaw(), added = [], gone = [];
    const t = raw.findIndex(isToc);
    if (t >= 0 && t === next.findIndex(isToc) && raw[t] !== next[t]) {   // 目录单独替换，不参与定位
      const n = make([next[t]])[0]; nodes[t].replaceWith(n); nodes[t] = n; raw[t] = next[t];
    }
    let p = 0; while (p < raw.length && p < next.length && raw[p] === next[p]) p++;
    let s = 0; while (s < raw.length - p && s < next.length - p && raw[raw.length - 1 - s] === next[next.length - 1 - s]) s++;
    const oldMid = nodes.slice(p, nodes.length - s), newMid = next.slice(p, next.length - s), tail = nodes.slice(nodes.length - s);
    let mid;
    if (oldMid.length === newMid.length) {            // 等长：逐块比较，只换真正变化的块
      mid = oldMid.map((n, i) => {
        if (raw[p + i] === newMid[i]) return n;
        const m = make([newMid[i]])[0]; n.replaceWith(m); gone.push(n); added.push(m); return m;
      });
    } else {
      mid = make(newMid); const anchor = tail[0] || end;
      oldMid.forEach(n => { n.remove(); gone.push(n); });
      mid.forEach(n => { document.body.insertBefore(n, anchor); added.push(n); });
    }
    nodes = [...nodes.slice(0, p), ...mid, ...tail]; raw = next;
    if (!added.length) return;
    MathJax.typesetClear?.(gone);
    await MathJax.typesetPromise(added);
    const r = added[0].getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight) added[0].scrollIntoView({block: "center"});
    added.forEach(n => n.classList.add("live-new"));
    setTimeout(() => added.forEach(n => n.classList.remove("live-new")), 1500);
  }
  async function loop() {
    for (;;) {
      try {
        const r = await (await fetch("/__live?v=" + v)).json();
        if (r.v === v) continue;
        const first = v < 0; v = r.v; banner(r.err);
        if (r.err || first) continue;
        if (ok && window.MathJax && MathJax.typesetPromise) await patch(); else location.reload();
      } catch (e) { await new Promise(r => setTimeout(r, 1000)); }
    }
  }
  document.addEventListener("DOMContentLoaded", async () => {
    nodes = Array.from(document.body.children);
    end = document.createElement("span"); end.hidden = true; document.body.appendChild(end);
    try { raw = await getRaw(); ok = raw.length === nodes.length; } catch (e) {}
    loop();
  });
})();
"""


class Live:
    v, err, cond = 0, "", threading.Condition()


def watch() -> None:
    sig = None
    while True:
        try:
            cur = tuple(sorted((str(p), p.stat().st_mtime_ns) for p in SRC.rglob("*") if p.is_file()))
        except OSError:
            cur = sig
        if cur != sig:
            sig, t0 = cur, time.time()
            try:
                err = build()
            except Exception as e:  # 构建器内部异常也显示到页面
                err = f"{type(e).__name__}: {e}"
            with Live.cond:
                Live.v, Live.err = Live.v + 1, err
                Live.cond.notify_all()
            print(f"[{time.strftime('%H:%M:%S')}] " + (f"构建失败\n{err}" if err else f"已刷新（{time.time() - t0:.2f}s）"), flush=True)
        time.sleep(0.2)


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *a) -> None:
        pass

    def _send(self, body: bytes, ctype: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        u = urlparse(self.path)
        if u.path == "/__live":
            v = int(parse_qs(u.query).get("v", ["-1"])[0])
            with Live.cond:
                Live.cond.wait_for(lambda: Live.v != v, timeout=20)
                body = json.dumps({"v": Live.v, "err": Live.err})
            return self._send(body.encode(), "application/json")
        if u.path in ("/", "/index.html", "/__raw"):
            f = SITE / "index.html"
            page = f.read_text(encoding="utf-8") if f.exists() else "<html><head></head><body><p>尚未构建成功。</p></body></html>"
            if u.path != "/__raw":
                page = page.replace("</head>", f"<script>{LIVE_JS}</script></head>", 1)
            return self._send(page.encode(), "text/html; charset=utf-8")
        super().do_GET()

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="构建一次")
    b.add_argument("-f", "--force", action="store_true", help="强制重编全部 TeX 算法/图")
    s = sub.add_parser("serve", help="监听 src/ 并实时预览")
    s.add_argument("--port", type=int, default=18767)
    args = ap.parse_args()
    if args.cmd == "build":
        err = build(args.force)
        print(err or f"OK  {SITE / 'index.html'}", file=sys.stderr if err else sys.stdout)
        return 1 if err else 0
    SITE.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=watch, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), lambda *a: Handler(*a, directory=str(SITE)))
    srv.daemon_threads = True
    print(f"预览：http://127.0.0.1:{args.port}/   （编辑 {SRC} 下的 .md，保存即刷新；Ctrl+C 退出）", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
