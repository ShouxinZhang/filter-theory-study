"""命令行入口：init / build / serve / import-tex / export-tex。"""
from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
import sys
from pathlib import Path

from .build import build_project
from .server.http import run_library_server, run_server
from .server.project import init_project


def cmd_init(args: argparse.Namespace) -> int:
    preset = getattr(args, "preset", "basic") or "basic"
    try:
        dest = init_project(
            Path(args.dir),
            title=getattr(args, "title", None),
            preset=preset,
            force=bool(getattr(args, "force", False)),
        )
    except (ValueError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 1
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
    lib = getattr(args, "library", None)
    force = bool(getattr(args, "force", False))
    if lib is not None:
        return run_library_server(
            library_root=Path(lib).resolve(),
            host=args.host,
            port=args.port,
            force_first=force,
        )
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
        force_first=force,
    )


def cmd_import_tex(args: argparse.Namespace) -> int:
    from .texsync.manifest import MANIFEST_NAME, execute_import

    raw = Path(args.tex_dir).resolve()
    out_opt = getattr(args, "out_html", None)
    if out_opt:
        tex_root, html_dir = raw, Path(out_opt).resolve()
    elif not (raw / "main.tex").is_file() and (raw / MANIFEST_NAME).is_file():
        try:
            meta = json.loads((raw / MANIFEST_NAME).read_text(encoding="utf-8"))
            rel_root = meta.get("tex_root", "..")
        except (OSError, ValueError):
            rel_root = ".."
        html_dir = raw
        tex_root = (raw / str(rel_root)).resolve()
    else:
        tex_root, html_dir = raw, raw / "html"
    return execute_import(
        tex_root,
        html_dir,
        check=bool(getattr(args, "check", False)),
        apply=bool(getattr(args, "apply", False)),
    )


def cmd_export_tex(args: argparse.Namespace) -> int:
    raw = Path(args.html_dir).resolve()
    default_tex: Path | None
    if not (raw / "src").is_dir() and (raw / "html" / "src").is_dir():
        html_dir, default_tex = raw / "html", raw
    else:
        html_dir, default_tex = raw, None
    to_opt = getattr(args, "to", None)
    tex_root = Path(to_opt).resolve() if to_opt else default_tex

    if getattr(args, "init_tex", False):
        from .texsync.scaffold import scaffold_tex_project

        return scaffold_tex_project(
            html_dir,
            tex_root=tex_root,
            apply=bool(getattr(args, "apply", False)),
            force=bool(getattr(args, "force", False)),
        )

    from .texsync.manifest import execute_export

    return execute_export(
        html_dir,
        tex_root=tex_root,
        apply=bool(getattr(args, "apply", False)),
    )


def main(argv: Sequence[str] | None = None) -> int:
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
    p_serve.add_argument(
        "--library",
        nargs="?",
        const="co-work 资产/tex-论文/论文集",
        default=None,
        help="以多论文工作区模式启动，可选指定论文库根目录（默认 co-work 资产/tex-论文/论文集）",
    )
    p_serve.add_argument("--src", help="显式指定源码目录（默认 <dir>/src）")
    p_serve.add_argument("--build-dir", help="显式指定 TeX 中间构建目录（默认 <dir>/build）")
    p_serve.add_argument("--out", help="显式指定站点输出目录（默认 <dir>/outputs/site）")
    p_serve.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    p_serve.add_argument("--port", type=int, default=18767, help="监听端口（默认 18767）")
    p_serve.add_argument("-f", "--force", action="store_true", help="首次构建时强制重编全部 TeX 图/算法")
    p_serve.set_defaults(func=cmd_serve)

    p_imp = sub.add_parser("import-tex", aliases=["tex2html"], help="将 LaTeX 工程确定性导入为受控学术 Markdown")
    p_imp.add_argument("tex_dir", nargs="?", default=".", help="TeX 工程根目录（默认当前目录）")
    p_imp.add_argument("-o", "--out-html", help="目标 HTML 工程目录（默认 <tex_dir>/html）")
    g_imp = p_imp.add_mutually_exclusive_group()
    g_imp.add_argument("--check", action="store_true", help="校验 F(TeX) == Markdown 零差异")
    g_imp.add_argument("--apply", action="store_true", help="原子写入 src/*.md 与 texsync.json（默认仅预览 diff）")
    p_imp.set_defaults(func=cmd_import_tex)

    p_exp = sub.add_parser("export-tex", aliases=["html2tex"], help="将受控学术 Markdown 最小差异回写或初始化父级 LaTeX 工程")
    p_exp.add_argument("html_dir", nargs="?", default=".", help="HTML 工程目录或含 html/src 的父目录（默认当前目录）")
    p_exp.add_argument("--to", help="显式指定目标 TeX 工程根目录")
    p_exp.add_argument("--init-tex", action="store_true", help="尚无父级 TeX 工程时机械生成 ctexart 工程与 texsync.json")
    p_exp.add_argument("-f", "--force", action="store_true", help="配合 --init-tex 允许覆盖已存在的 main.tex")
    p_exp.add_argument("--apply", action="store_true", help="校验通过后原子写盘（默认仅预览 diff 或文件清单）")
    p_exp.set_defaults(func=cmd_export_tex)

    args = parser.parse_args(list(argv) if argv is not None else None)
    return args.func(args)
