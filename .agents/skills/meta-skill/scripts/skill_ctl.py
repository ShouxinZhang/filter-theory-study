#!/usr/bin/env python3
"""meta-skill: 仓库 Skill 脚手架、子技能收纳与规范体检 CLI

用法:
  skill_ctl.py init <name> [-d DESC] [--parent GROUP] [--router]
  skill_ctl.py pack <skill> --into <group> [-s 场景说明]
  skill_ctl.py lint [skill_path]
"""
import argparse, re, shutil, sys
from pathlib import Path

REPO = Path(__file__).resolve()
while REPO != REPO.parent and not (REPO / ".git").exists():
    REPO = REPO.parent
SKILLS_DIR = REPO / ".agents/skills"
TMPL_DIR = Path(__file__).resolve().parent.parent / "references/templates"
ALLOWED_EXTRA = {"tests", "agents", "examples", "resources", ".gitignore", "HOST_PROFILE.md"}


def parse_frontmatter(text):
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return {}
    out = {}
    for ln in m.group(1).splitlines():
        if ":" in ln:
            k, v = ln.split(":", 1)
            out[k.strip()] = v.strip().strip("'\"")
    return out


def register_in_router(group_dir: Path, sub_name: str, scene: str):
    router_md = group_dir / "SKILL.md"
    if not router_md.exists():
        return
    txt = router_md.read_text(encoding="utf-8")
    link = f"[{sub_name}/SKILL.md]({sub_name}/SKILL.md)"
    row = f"| {scene} | {sub_name} | {link} |"
    if f"| {sub_name} |" in txt:
        txt = re.sub(rf"^\|[^\n]*\|\s*{re.escape(sub_name)}\s*\|[^\n]*$", row, txt, flags=re.M)
    else:
        txt = re.sub(r"(\| --- \| --- \| --- \|\r?\n)", rf"\1{row}\n", txt, count=1)
    router_md.write_text(txt, encoding="utf-8")


def cmd_init(args):
    target = (SKILLS_DIR / args.parent / args.name) if args.parent else (SKILLS_DIR / args.name)
    if target.exists():
        print(f"错误: {target} 已存在", file=sys.stderr)
        return 1
    target.mkdir(parents=True)
    desc = args.description or f"{args.name} 技能说明"
    if args.router:
        tmpl = (TMPL_DIR / "router-SKILL.md").read_text(encoding="utf-8")
        (target / "SKILL.md").write_text(tmpl.format(name=args.name, description=desc), encoding="utf-8")
    else:
        (target / "references").mkdir()
        (target / "scripts").mkdir()
        (target / "references/README.md").write_text(f"# {args.name} 参考细则\n", encoding="utf-8")
        script_name = f"{args.name.replace('-', '_')}.py"
        sp = target / "scripts" / script_name
        sp.write_text(
            '#!/usr/bin/env python3\nimport argparse\nif __name__ == "__main__":\n'
            f'    ap = argparse.ArgumentParser(description="{args.name}")\n    ap.parse_args()\n',
            encoding="utf-8",
        )
        sp.chmod(0o755)
        rel = target.relative_to(REPO)
        tmpl = (TMPL_DIR / "atomic-SKILL.md").read_text(encoding="utf-8")
        (target / "SKILL.md").write_text(
            tmpl.format(name=args.name, description=desc, rel_path=rel, script_name=script_name),
            encoding="utf-8",
        )
        if args.parent:
            register_in_router(SKILLS_DIR / args.parent, args.name, desc)
    print(f"已创建: {target.relative_to(REPO)}")
    return 0


def cmd_pack(args):
    src = SKILLS_DIR / args.skill
    group = SKILLS_DIR / args.into
    dst = group / args.skill
    if not src.is_dir():
        print(f"错误: 源技能 {src} 不存在", file=sys.stderr)
        return 1
    if not (group / "SKILL.md").exists():
        print(f"错误: 目标路由组 {group} 不存在或缺少 SKILL.md", file=sys.stderr)
        return 1
    if dst.exists():
        print(f"错误: 目标 {dst} 已存在", file=sys.stderr)
        return 1
    old_rel = f".agents/skills/{args.skill}"
    new_rel = f".agents/skills/{args.into}/{args.skill}"
    shutil.move(str(src), str(dst))
    for md in list(dst.rglob("*.md")) + list(dst.rglob("*.py")) + [group / "SKILL.md"]:
        if md.is_file():
            c = md.read_text(encoding="utf-8")
            c2 = c.replace(old_rel, new_rel).replace(f"../{args.skill}/SKILL.md", f"{args.skill}/SKILL.md")
            if c2 != c:
                md.write_text(c2, encoding="utf-8")
    fm = parse_frontmatter((dst / "SKILL.md").read_text(encoding="utf-8"))
    scene = args.scene or fm.get("description", args.skill)
    register_in_router(group, args.skill, scene)
    print(f"已收纳: {old_rel} -> {new_rel}")
    return 0


def lint_one(skill_dir: Path, is_sub=False):
    issues = []
    rel = skill_dir.relative_to(REPO)
    md = skill_dir / "SKILL.md"
    if not md.exists():
        return [f"{rel}: 缺少 SKILL.md"]
    txt = md.read_text(encoding="utf-8")
    fm = parse_frontmatter(txt)
    if not fm.get("name") or not fm.get("description"):
        issues.append(f"{rel}/SKILL.md: Frontmatter 缺少 name 或 description")
    lines = len(txt.splitlines())
    if lines > 90:
        issues.append(f"{rel}/SKILL.md: 行数 {lines} > 90 (建议下沉到 references/)")
    clean_txt = re.sub(r"```.*?```|`[^`\n]+`", "", txt, flags=re.S)
    for m in re.finditer(r"\]\(([^)#]+)(?:#[^)]*)?\)", clean_txt):
        target = m.group(1)
        if "://" in target or target.startswith("/"):
            continue
        if not (skill_dir / target).exists():
            issues.append(f"{rel}/SKILL.md: 死链 -> {target}")
    subs = [d for d in sorted(skill_dir.iterdir())
            if d.is_dir() and d.name not in {"references", "scripts"} | ALLOWED_EXTRA and (d / "SKILL.md").exists()]
    for sub in subs:
        if f"{sub.name}/SKILL.md" not in txt:
            issues.append(f"{rel}/SKILL.md: 未在路由表登记子技能 {sub.name}")
        issues.extend(lint_one(sub, is_sub=True))
    return issues


def cmd_lint(args):
    targets = [Path(args.path).resolve()] if args.path else [
        d for d in sorted(SKILLS_DIR.iterdir()) if d.is_dir() and not d.name.startswith(".")
    ]
    all_issues = []
    for t in targets:
        all_issues.extend(lint_one(t))
    if all_issues:
        for it in all_issues:
            print(f"[WARN] {it}")
        return 1
    print(f"OK: 已检查 {len(targets)} 个顶层技能组/技能, 全部符合规范.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="meta-skill 管理工具")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init", help="创建新技能骨架 (三块结构或路由组)")
    p_init.add_argument("name", help="技能名")
    p_init.add_argument("-d", "--description", help="一句话描述")
    p_init.add_argument("--parent", help="作为子技能挂载到指定父路由组下")
    p_init.add_argument("--router", action="store_true", help="创建为顶层路由组")

    p_pack = sub.add_parser("pack", help="将独立顶层技能物理收纳进父路由组")
    p_pack.add_argument("skill", help="待收纳的顶层技能名")
    p_pack.add_argument("--into", required=True, help="目标父路由组名 (如 tmp)")
    p_pack.add_argument("-s", "--scene", help="路由表中的场景说明")

    p_lint = sub.add_parser("lint", help="校验技能结构、行数、Frontmatter 与死链")
    p_lint.add_argument("path", nargs="?", help="指定技能目录 (默认检查全部)")

    a = ap.parse_args()
    sys.exit({"init": cmd_init, "pack": cmd_pack, "lint": cmd_lint}[a.cmd](a))
