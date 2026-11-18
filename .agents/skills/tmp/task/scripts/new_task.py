#!/usr/bin/env python3
"""创建或补全 .agents/.tmp/task/<周日_周六>/<YYYY-MM-DD_HH-mm_任务名>/ 任务目录及 docs/ 存档骨架.

周目录与 .tmp/agent 一致: 周日 00:00 至下周日 00:00 前 (Asia/Singapore), 名为 YYYY-MM-DD_YYYY-MM-DD.

docs/ 下按类型分为三个子目录, 每类均可多份:
  plans/YYYY-MM-DD_HH-mm_<标题>.md    计划 (初始计划, 修订计划...)
  logs/YYYY-MM-DD_HH-mm_<slug>.md     日志, 一个用户 prompt 一份, 作为该 prompt 的验收索引
  reports/YYYY-MM-DD_HH-mm_<标题>.md  重型汇报 (仅在需要时生成)
子任务 (子代理) 位于 tasks/<slug>/: brief.md, logs/, agents/<名称>/ (子代理唯一可写区).
任务跨日继续时沿用原目录, 以新 log 区分.

模板位于 ../references/templates/, 占位符: {header} {name} {start} {prompt} {title} {related} {slug}.

用法:
  python3 new_task.py -n ocr-book -p "用户原始 prompt"              # 新建任务: 初始计划 + 首份 log
  python3 new_task.py -n ocr-book --log-new "fix-crash" -p "..."     # 新的用户 prompt: 新建一份 log
  python3 new_task.py -n ocr-book --log "完成第 1 步"                # 向最新一份 log 的时间线追加事件
  python3 new_task.py -n ocr-book --plan "修订: 改用 GPU"            # 追加一份计划
  python3 new_task.py -n ocr-book --report "基线对比"                # 追加一份报告
  python3 new_task.py -n ocr-book --subtask "math-review"            # 新建子任务区 (brief + 子日志)
  python3 new_task.py -n ocr-book --migrate                          # 旧版 docs 布局迁移
  python3 new_task.py --relayout [--dry-run]                         # 旧 YYYY-MM/YYYY-MM-DD_名 迁入周目录
"""
import argparse
import os
import re
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[5]
TASK_ROOT = ROOT / ".agents/.tmp/task"
TZ = ZoneInfo("Asia/Singapore")
TEMPLATES = Path(__file__).resolve().parents[1] / "references" / "templates"
GET_MODEL = ROOT / ".agents/skills/get-model-name/scripts/get_model_name.py"
KINDS = ("plans", "logs", "reports")
TL_HEAD = "## 3. 时间线"


def now(fmt="%Y-%m-%d %H:%M"):
    return datetime.now(TZ).strftime(fmt)


def model_info(header: bool = False) -> str:
    """调用 get-model-name; header=True 时返回 model/harness/session/time 署名块."""
    try:
        out = subprocess.run(
            ["python3", str(GET_MODEL)] + (["--header"] if header else []),
            capture_output=True, text=True, timeout=20,
        ).stdout.strip()
    except Exception:
        out = ""
    return out or ("- agent name: unknown" if header else "unknown")


DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(?:(\d{2}-\d{2})_)?(.+)$")


def week_dir(d: date) -> str:
    """d 所在周的目录名: <周日>_<周六>."""
    sun = d - timedelta(days=(d.weekday() + 1) % 7)
    return f"{sun:%Y-%m-%d}_{sun + timedelta(days=6):%Y-%m-%d}"


def find_task(pattern: str):
    """在周目录, 旧月目录及根目录下查找任务目录, 取名称排序最后者."""
    hits = [p for p in TASK_ROOT.glob(f"*/{pattern}") if p.is_dir()]
    hits += [p for p in TASK_ROOT.glob(pattern) if p.is_dir()]
    return sorted(hits, key=lambda p: p.name)[-1] if hits else None


def resolve_dir(name: str) -> Path:
    """带日期前缀时按日期 (可含 HH-mm) 定位; 否则匹配已有 *_任务名 (跨日跨周续用原目录); 均无则在当周新建."""
    if m := DATE_RE.match(name):
        dd, hm, rest = m.groups()
        hit = find_task(name) or (None if hm else find_task(f"{dd}_??-??_{rest}"))
        if hit:
            return hit
        d = date.fromisoformat(dd)
        return TASK_ROOT / week_dir(d) / (name if hm else f"{dd}_{now('%H-%M')}_{rest}")
    hit = find_task(f"????-??-??_??-??_{name}") or find_task(f"????-??-??_{name}")
    if hit:
        return hit
    return TASK_ROOT / week_dir(datetime.now(TZ).date()) / f"{now('%Y-%m-%d_%H-%M')}_{name}"


def first_stamp(d: Path, day: str):
    """目录内与 day 同日的最早 plan/log 文件名时间戳 HH-mm."""
    stamps = sorted(q.name[11:16] for k in ("plans", "logs") for q in (d / "docs" / k).glob(f"{day}_??-??_*.md"))
    return stamps[0] if stamps else None


def relayout(dry: bool):
    """旧布局 YYYY-MM/YYYY-MM-DD[_HH-mm]_名 或根目录平铺 → <周目录>/YYYY-MM-DD_HH-mm_名."""
    olds = [p for p in TASK_ROOT.glob("????-??/*") if p.is_dir()]
    olds += [p for p in TASK_ROOT.glob("????-??-??_*") if p.is_dir() and not re.match(r"^\d{4}-\d{2}-\d{2}_\d{4}-", p.name)]
    for src in sorted(olds, key=lambda p: p.name):
        m = DATE_RE.match(src.name)
        if not m:
            print(f"skip (无日期前缀) {src.relative_to(TASK_ROOT)}")
            continue
        dd, hm, rest = m.groups()
        basis = "目录名"
        if not hm:
            hm, basis = first_stamp(src, dd), "最早 plan/log"
            if not hm:
                mt = datetime.fromtimestamp(src.stat().st_mtime, TZ)
                hm, basis = (mt.strftime("%H-%M"), "目录 mtime") if mt.strftime("%Y-%m-%d") == dd else ("00-00", "缺省 00-00")
        dst = TASK_ROOT / week_dir(date.fromisoformat(dd)) / f"{dd}_{hm}_{rest}"
        print(f"{src.relative_to(TASK_ROOT)}\t{dst.relative_to(TASK_ROOT)}\t{basis}")
        if dry:
            continue
        if dst.exists():
            print(f"  skip: 目标已存在")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
    if not dry:
        for mdir in TASK_ROOT.glob("????-??"):
            if mdir.is_dir() and not any(mdir.iterdir()):
                mdir.rmdir()
                print(f"removed empty {mdir.name}/")


def slug(title: str) -> str:
    """文件名用标题: 去除路径分隔符与空白, 保留中文."""
    s = re.sub(r"[\\/:*?\"<>|\s]+", "-", title.strip()).strip("-")
    return s[:60] or "untitled"


def render(tpl: str, ctx: dict) -> str:
    return (TEMPLATES / f"{tpl}.md").read_text(encoding="utf-8").format(**ctx)


def stamped(folder: Path, title: str) -> Path:
    """folder/<YYYY-MM-DD_HH-mm>_<slug>.md; 同名时追加序号."""
    folder.mkdir(parents=True, exist_ok=True)
    base = f"{now('%Y-%m-%d_%H-%M')}_{slug(title)}"
    p, i = folder / f"{base}.md", 2
    while p.exists():
        p, i = folder / f"{base}-{i}.md", i + 1
    return p


def write_new(p: Path, tpl: str, ctx: dict) -> Path:
    p.write_text(render(tpl, ctx), encoding="utf-8")
    print(f"created {p.relative_to(ROOT)}")
    return p


def latest_log(docs: Path):
    """当前活动 log: 优先读 docs/logs/.current (同一分钟内多份 log 时文件名排序不可靠), 否则取时间戳最大者."""
    cur = docs / "logs" / ".current"
    if cur.exists() and (p := docs / "logs" / cur.read_text(encoding="utf-8").strip()).exists():
        return p
    logs = sorted((docs / "logs").glob("*.md"), key=lambda q: q.name[:16])
    return logs[-1] if logs else None


def set_current(log: Path):
    (log.parent / ".current").write_text(log.name, encoding="utf-8")


def rel(p, start: Path) -> str:
    return os.path.relpath(p, start) if p else "无"


def append_event(log: Path, event: str):
    """在 log 的时间线小节末尾追加一行; 旧版 log 无该小节时追加到文末."""
    s = log.read_text(encoding="utf-8")
    line = f"- {now()} — {event}\n"
    if TL_HEAD in s:
        head, rest = s.split(TL_HEAD, 1)
        m = re.search(r"\n## ", rest)
        section, tail = (rest[: m.start()], rest[m.start():]) if m else (rest, "")
        s = head + TL_HEAD + section.rstrip("\n") + "\n" + line + tail
    else:
        s = s.rstrip("\n") + "\n" + line
    log.write_text(s, encoding="utf-8")
    print(f"logged -> {log.name}: {event}")


def migrate(docs: Path):
    """旧版布局迁移: docs/{plan,logs,report}.md 迁入子目录; 按日 log 改名为 <日期>_00-00_legacy.md."""
    stamp = lambda p: datetime.fromtimestamp(p.stat().st_mtime, TZ).strftime("%Y-%m-%d_%H-%M")
    moves = []
    if (p := docs / "plan.md").exists():
        m = re.search(r"开始时间:\s*(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2})", p.read_text(encoding="utf-8"))
        ts = f"{m[1]}_{m[2]}-{m[3]}" if m else stamp(p)
        moves.append((p, docs / "plans" / f"{ts}_初始计划.md"))
    if (p := docs / "logs.md").exists():
        m = re.search(r"^- (\d{4}-\d{2}-\d{2}) ", p.read_text(encoding="utf-8"), re.M)
        moves.append((p, docs / "logs" / f"{m[1] if m else stamp(p)[:10]}_00-00_legacy.md"))
    if (p := docs / "report.md").exists():
        moves.append((p, docs / "reports" / f"{stamp(p)}_报告.md"))
    for p in (docs / "logs").glob("????-??-??.md"):
        moves.append((p, p.with_name(f"{p.stem}_00-00_legacy.md")))
    for src, dst in moves:
        if dst.exists():
            print(f"skip {src.name}: {dst.relative_to(ROOT)} 已存在")
            continue
        src.rename(dst)
        print(f"moved {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--name", help="任务名, 可带或不带日期前缀")
    ap.add_argument("-p", "--prompt", default="(待补充)", help="用户原始 prompt")
    ap.add_argument("--log-new", default=None, help="新的用户 prompt: 新建一份 log, 参数为 slug")
    ap.add_argument("--log", default=None, help="向最新一份 log 的时间线追加事件")
    ap.add_argument("--plan", nargs="?", const="修订计划", default=None, help="新增一份计划, 可给标题")
    ap.add_argument("--report", nargs="?", const="报告", default=None, help="新增一份报告, 可给标题")
    ap.add_argument("--subtask", default=None, help="新建子任务区 tasks/<slug>/")
    ap.add_argument("--agent", nargs="+", default=None, help="在子任务区下初始化子代理目录 agents/<name>/docs/reports/")
    ap.add_argument("--migrate", action="store_true", help="旧版 docs 布局迁移")
    ap.add_argument("--relayout", action="store_true", help="旧 YYYY-MM 按日目录迁入周目录")
    ap.add_argument("--dry-run", action="store_true", help="与 --relayout 同用: 仅打印映射")
    a = ap.parse_args()
    if a.relayout:
        return relayout(a.dry_run)
    if not a.name:
        ap.error("-n/--name 必填 (除 --relayout 外)")

    d = resolve_dir(a.name)
    docs = d / "docs"
    fresh = not docs.exists()
    for k in KINDS:
        (docs / k).mkdir(parents=True, exist_ok=True)
    if a.migrate:
        migrate(docs)
    ctx = dict(header=model_info(header=True), name=d.name, start=now(), slug="",
               prompt=a.prompt.replace("\n", "\n> "), title="", related="无")

    if not any((docs / "plans").glob("*.md")):
        write_new(stamped(docs / "plans", "初始计划"), "plan", {**ctx, "title": "初始计划"})
    if fresh and not a.log_new:
        set_current(write_new(stamped(docs / "logs", "创建任务"), "log", {**ctx, "title": "创建任务"}))
    if a.log_new:
        p = stamped(docs / "logs", a.log_new)
        prev = latest_log(docs)
        write_new(p, "log", {**ctx, "title": a.log_new, "related": f"上一份 {rel(prev, p.parent)}"})
        if prev:
            append_event(prev, f"转入 {p.name}")
        set_current(p)
    if a.plan:
        write_new(stamped(docs / "plans", a.plan), "plan", {**ctx, "title": a.plan})
    if a.report and not (a.subtask and a.agent):
        write_new(stamped(docs / "reports", a.report), "report", {**ctx, "title": a.report})
    if a.subtask:
        s = slug(a.subtask)
        t = d / "tasks" / s
        (t / "agents").mkdir(parents=True, exist_ok=True)
        parent = latest_log(docs)
        sctx = {**ctx, "title": a.subtask, "slug": s}
        if not (t / "brief.md").exists():
            write_new(t / "brief.md", "brief", {**sctx, "related": rel(parent, t)})
        if not any((t / "logs").glob("*.md")) if (t / "logs").exists() else True:
            sl = stamped(t / "logs", s)
            write_new(sl, "log", {**sctx, "related": f"父日志 {rel(parent, sl.parent)}; brief ../brief.md"})
            if parent:
                append_event(parent, f"开启子任务 tasks/{s}/")
        if a.agent:
            for ag in a.agent:
                ag_slug = slug(ag)
                ag_docs = t / "agents" / ag_slug / "docs"
                (ag_docs / "reports").mkdir(parents=True, exist_ok=True)
                (ag_docs / "logs").mkdir(parents=True, exist_ok=True)
                print(f"initialized {(ag_docs / 'reports').relative_to(ROOT)}")
                if a.report:
                    write_new(stamped(ag_docs / "reports", a.report), "report",
                              {**ctx, "name": f"{d.name}/{s}/{ag_slug}", "title": a.report})
    if a.log:
        log = latest_log(docs)
        if log is None:
            log = write_new(stamped(docs / "logs", "session"), "log", {**ctx, "title": "session"})
            set_current(log)
        append_event(log, a.log)
    print(d.relative_to(ROOT))


if __name__ == "__main__":
    main()
