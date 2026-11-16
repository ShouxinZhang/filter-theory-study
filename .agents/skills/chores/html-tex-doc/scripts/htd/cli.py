"""命令行入口：init / build / serve。"""
from __future__ import annotations

import argparse
import html
import shutil
import sys
from pathlib import Path

from .build import build_project
from .paths import TEMPLATE_ACADEMIC, TEMPLATE_BASIC
from .server.http import run_server

def cmd_init(args: argparse.Namespace) -> int:
    preset = getattr(args, "preset", "basic") or "basic"
    tpl = TEMPLATE_ACADEMIC if preset == "academic-md" else TEMPLATE_BASIC
    if not tpl.exists():
        print(f"找不到预设模板目录：{tpl}", file=sys.stderr)
        return 1
    dest = Path(args.dir).resolve() / "src"
    if dest.exists() and any(dest.iterdir()) and not args.force:
        print(f"目标已存在且非空：{dest}（如需覆盖请加 --force）", file=sys.stderr)
        return 1
    if dest.exists() and args.force:
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(tpl, dest)
    if not (dest / "common.tex").exists() and (TEMPLATE_BASIC / "common.tex").exists():
        shutil.copy(TEMPLATE_BASIC / "common.tex", dest / "common.tex")
    if args.title:
        for candidate in (dest / "doc.html", dest / "00_摘要.md", dest / "01_正文.md"):
            if candidate.exists():
                txt = candidate.read_text(encoding="utf-8")
                txt = txt.replace("<!-- title: 文档标题 -->", f"<!-- title: {args.title} -->", 1)
                txt = txt.replace("<h1>文档标题</h1>", f"<h1>{html.escape(args.title)}</h1>", 1)
                candidate.write_text(txt, encoding="utf-8")
    print(f"已初始化混合文档骨架（preset={preset}）：{dest}")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    base = Path(args.dir).resolve()
    src_dir = Path(args.src).resolve() if getattr(args, "src", None) else base / "src"
    build_dir = Path(args.build_dir).resolve() if getattr(args, "build_dir", None) else base / "build"
    out_dir = Path(args.out).resolve() if getattr(args, "out", None) else base / "outputs" / "site"
    rc, msg, _ = build_project(src_dir, build_dir, out_dir, force=bool(getattr(args, "force", False)))
    print(msg, file=sys.stderr if rc else sys.stdout)
    return rc


def cmd_serve(args: argparse.Namespace) -> int:
    from .server.http import run_server

    base = Path(args.dir).resolve()
    src_dir = Path(args.src).resolve() if getattr(args, "src", None) else base / "src"
    build_dir = Path(args.build_dir).resolve() if getattr(args, "build_dir", None) else base / "build"
    out_dir = Path(args.out).resolve() if getattr(args, "out", None) else base / "outputs" / "site"
    return run_server(
        src_dir=src_dir,
        build_dir=build_dir,
        out_dir=out_dir,
        host=args.host,
        port=args.port,
        force_first=bool(getattr(args, "force", False)),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="无分页 HTML / Markdown 正文 + TeX 出图混合文档构建与实时编辑工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="在指定目录下生成 src/ 空白工程骨架")
    p_init.add_argument("dir", help="目标工程根目录")
    p_init.add_argument("-t", "--title", help="初始文档标题")
    p_init.add_argument("--preset", choices=["basic", "academic-md"], default="basic", help="骨架模板预设（默认 basic）")
    p_init.add_argument("-f", "--force", action="store_true", help="覆盖已存在的 src/ 目录")
    p_init.set_defaults(func=cmd_init)

    p_build = sub.add_parser("build", help="构建混合文档为单页静态站点")
    p_build.add_argument("dir", nargs="?", default=".", help="工程根目录（默认当前目录）")
    p_build.add_argument("--src", help="显式指定源码目录（默认 <dir>/src）")
    p_build.add_argument("--build-dir", help="显式指定 TeX 中间构建目录（默认 <dir>/build）")
    p_build.add_argument("--out", help="显式指定站点输出目录（默认 <dir>/outputs/site）")
    p_build.add_argument("-f", "--force", action="store_true", help="忽略缓存，强制重编全部 TeX 图/算法")
    p_build.set_defaults(func=cmd_build)

    p_serve = sub.add_parser("serve", help="启动本地实时预览与 Web 双栏编辑服务器")
    p_serve.add_argument("dir", nargs="?", default=".", help="工程根目录（默认当前目录）")
    p_serve.add_argument("--src", help="显式指定源码目录（默认 <dir>/src）")
    p_serve.add_argument("--build-dir", help="显式指定 TeX 中间构建目录（默认 <dir>/build）")
    p_serve.add_argument("--out", help="显式指定站点输出目录（默认 <dir>/outputs/site）")
    p_serve.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    p_serve.add_argument("--port", type=int, default=18767, help="监听端口（默认 18767）")
    p_serve.add_argument("-f", "--force", action="store_true", help="首次构建时强制重编全部 TeX 图/算法")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    return args.func(args)
