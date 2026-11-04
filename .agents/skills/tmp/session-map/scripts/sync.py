#!/usr/bin/env python3
"""session-map: 将 Antigravity / Codex 本地会话同步为渐进折叠的 prompts.md

用法:
  sync.py <id|前缀>         初始化/单次同步指定会话 (创建 map.md 模板 + 生成 prompts.md)
  sync.py --all             单次同步 .agents/.tmp/session/ 下所有已订阅会话
  sync.py --watch           常驻监听: 轮询已订阅会话的 transcript_full.jsonl mtime_ns
  sync.py --install-service 安装并启动 systemd --user 常驻服务 (session-map-sync.service)
  sync.py --status-service  查看 systemd --user 服务状态

约定:
  - 机械文件 .agents/.tmp/session/<id>/prompts.md 由脚本原子覆盖, 人类勿手改
  - 草稿文件 .agents/.tmp/session/<id>/map.md 仅在不存在时创建模板, 脚本永不覆盖
"""
import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
from codex import parse_turns as codex_turns

BRAIN = Path.home() / ".gemini/antigravity/brain"
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
REPO = Path(__file__).resolve()
while REPO != REPO.parent and not (REPO / ".git").exists():
    REPO = REPO.parent
SESS = REPO / ".agents/.tmp/session"
SERVICE_NAME = "session-map-sync.service"
SERVICE_PATH = Path.home() / ".config/systemd/user" / SERVICE_NAME
TZ = timezone(timedelta(hours=8))

MAP_TMPL = """# map · {sid8}

<!-- 人写区域, 脚本永不覆盖. 引用原件: [p1](prompts.md#p1) -->

## 主线

- [ ] [p1](prompts.md#p1)

## 支线

- 

## 待办 / 迷失时看这里

- 
"""


def ts(s):
    value = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(TZ)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fence(body, lang=""):
    n = max([3] + [len(m) + 1 for m in re.findall(r"`{3,}", body)])
    f = "`" * n
    return f"{f}{lang}\n{body.rstrip()}\n{f}"


def details(summary, body, open_=False):
    o = " open" if open_ else ""
    return f"<details{o}><summary>{esc(summary)}</summary>\n\n{body.strip()}\n\n</details>"


def user_text(c):
    m = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", c or "", re.S)
    return (m.group(1) if m else (c or "")).strip()


def tool_title(tc):
    a, n = tc.get("args", {}), tc.get("name", "?")
    if n == "run_command":
        return f"Ran {a.get('toolSummary') or 'command'}"
    if n in {"exec", "exec_command", "functions.exec_command", "functions.exec"}:
        return f"Ran {n}"
    p = a.get("Path") or a.get("TargetFile") or ""
    base = os.path.basename(p) if p else ""
    verb = {"write_file": "Wrote", "edit_file": "Edited", "read_file": "Read"}.get(n, n)
    return f"{verb} {base}".strip()


def tool_body(tc, result):
    a, n = tc.get("args", {}), tc.get("name", "?")
    if n == "run_command":
        head = fence(a.get("CommandLine", ""), "bash")
    elif n in {"exec", "functions.exec"} and isinstance(a.get("input"), str):
        head = fence(a["input"], "javascript")
    elif n in {"exec_command", "functions.exec_command"}:
        head = fence(a.get("cmd", ""), "bash")
    elif n == "write_file":
        head = f"`{a.get('Path','')}`\n\n" + fence(a.get("Content", ""), "markdown")
    elif n == "edit_file":
        head = (f"`{a.get('Path','')}`\n\n" + fence(a.get("Target", ""), "text")
                + "\n\n→\n\n" + fence(a.get("Replacement", ""), "text"))
    else:
        head = fence(json.dumps(a, ensure_ascii=False, indent=2), "json")
    result = tc.get("result", result)
    out = "_(等待输出)_" if tc.get("pending") else "_(无输出)_"
    if result:
        out = fence(result, "text")
    return f"{head}\n\n{out}"


def turns(steps):
    cur = None
    for d in steps:
        if d.get("type") == "USER_INPUT":
            if cur:
                yield cur
            cur = {"user": d, "steps": []}
        elif cur:
            cur["steps"].append(d)
    if cur:
        yield cur


def thought_label(st, i):
    if st[i].get("thought_label"):
        return st[i]["thought_label"]
    if i + 1 < len(st):
        try:
            dt = max(0, int((ts(st[i + 1]["created_at"]) - ts(st[i]["created_at"])).total_seconds()))
            if dt > 0:
                return f"Thought for {dt}s"
        except Exception:
            pass
    return "Thought"


def render_turn(k, t):
    u = t["user"]
    st = t["steps"]
    when = ts(u["created_at"])
    lines = [f'<a id="p{k}"></a>', "", f"## p{k} · {when:%m-%d %H:%M}", ""]
    txt = esc(user_text(u.get("content")))
    lines += ["> " + (ln + "  " if ln else "") for ln in txt.splitlines()] + [""]
    for m in u.get("media") or []:
        lines.append(f"- 📎 [{os.path.basename(m.get('uri',''))}](file://{m.get('uri','')})")
    final_i = None
    for i, d in enumerate(st):
        if (d.get("type") == "PLANNER_RESPONSE" and d.get("content")
                and not d.get("tool_calls") and d.get("phase") != "commentary"):
            final_i = i
    inner, pending = [], []
    for i, d in enumerate(st):
        if i == final_i:
            if d.get("thinking"):
                inner.append(details(thought_label(st, i), esc(d["thinking"])))
            continue
        ty = d.get("type")
        if ty == "PLANNER_RESPONSE":
            if d.get("thinking"):
                inner.append(details(thought_label(st, i), esc(d["thinking"])))
            if d.get("content"):
                inner.append(d["content"])
            pending = list(d.get("tool_calls") or [])
            if not pending:
                continue
            j, res = i + 1, []
            while j < len(st) and st[j].get("type") == "GENERIC" and len(res) < len(pending):
                res.append(st[j].get("content", "")); j += 1
            for tc, r in zip(pending, res + [""] * (len(pending) - len(res))):
                inner.append(details(tool_title(tc), tool_body(tc, r)))
        elif ty == "ERROR_MESSAGE":
            inner.append(details("⚠ Error", fence(d.get("error", ""), "text")))
    if st or t.get("status"):
        ended = t.get("ended_at") or t.get("last_activity_at") or (st[-1]["created_at"] if st else u["created_at"])
        dur = t.get("duration_seconds", max(0, int((ts(ended) - when).total_seconds())))
        nt = sum(len(d.get("tool_calls") or []) for d in st)
        status = {"working": "Working", "interrupted": "Interrupted"}.get(t.get("status"), "Worked")
        lines += ["", details(f"{status} for {dur}s · {nt} tools", "\n\n".join(inner) or "_(空)_")]
    if final_i is not None:
        lines += ["", st[final_i]["content"].strip()]
    lines += ["", "---", ""]
    return "\n".join(lines)


def read_snapshot(src):
    """Read a snapshot, allowing only an unfinished final JSONL record."""
    lines = src.read_bytes().splitlines(keepends=True)
    records = []
    incomplete_tail = False
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except (ValueError, UnicodeDecodeError):
            if index == len(lines) - 1 and not line.endswith(b"\n"):
                incomplete_tail = True
                break
            raise ValueError(f"{src}:{index + 1}: 无效 JSONL 记录") from None
    return records, incomplete_tail


def read_records(src):
    return read_snapshot(src)[0]


def attribution():
    script = REPO / ".agents/skills/get-model-name/scripts/get_model_name.py"
    try:
        result = subprocess.run([sys.executable, str(script), "--header"],
                                capture_output=True, text=True, timeout=20, check=True)
        if all(f"- {key}:" in result.stdout for key in ("agent name", "harness", "session", "time")):
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ("- agent name: unknown\n- harness: unknown\n- session: unknown\n"
            f"- time: {datetime.now(TZ):%Y-%m-%d %H:%M} (Asia/Shanghai)")


def render(sid, src, harness="antigravity", header=None, records=None):
    if records is None:
        records = read_records(src)
    ts_ = codex_turns(records) if harness == "codex" else list(turns(records))
    idx = []
    for k, t in enumerate(ts_, 1):
        ut = user_text(t["user"].get("content"))
        first = ut.splitlines()[0][:60] if ut else ""
        idx.append(f"- [p{k}](#p{k}) {esc(first)}")
    head = (f"{header or attribution()}\n\n# prompts · {sid[:8]}\n\n"
            f"来源 harness `{harness}`，会话 `{sid}`。\n\n"
            f"<!-- 机械文件, sync.py 自动生成, 勿手改. "
            f"源: {src} · 同步于 {datetime.now(TZ):%Y-%m-%d %H:%M:%S} -->\n\n"
            + "\n".join(idx) + "\n\n---\n\n")
    return head + "\n".join(render_turn(k, t) for k, t in enumerate(ts_, 1))


@dataclass(frozen=True)
class Source:
    sid: str
    harness: str
    path: Path


def validate_id(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{7,}", value):
        raise ValueError("会话 ID 须为至少 8 位的字母、数字、连字符或下划线")


def source_from_path(path, harness="auto", prefix=None):
    path = path.expanduser().resolve()
    records = read_records(path)
    meta = next((r.get("payload", {}) for r in records if r.get("type") == "session_meta"), None)
    actual = "codex" if meta is not None else "antigravity"
    if harness not in {"auto", actual}:
        raise ValueError(f"日志格式为 {actual}，与 --harness {harness} 不符")
    if actual == "codex":
        sid = meta.get("id", "")
    else:
        if not any(r.get("type") == "USER_INPUT" for r in records):
            raise ValueError(f"{path}: 未识别到会话元数据或 USER_INPUT")
        sid = path.parents[2].name
    validate_id(sid)
    if prefix and not sid.startswith(prefix):
        raise ValueError(f"日志中的会话 {sid} 与请求的 {prefix} 不符")
    return Source(sid, actual, path)


def resolve_source(prefix, harness="auto", source_path=None):
    if prefix:
        validate_id(prefix)
    if source_path:
        return source_from_path(source_path, harness, prefix)
    if not prefix:
        raise ValueError("需要会话 ID、--current 或 --source")
    metadata = SESS / prefix / ".source.json"
    if metadata.exists():
        saved = read_json(metadata)
        if harness not in {"auto", saved["harness"]}:
            raise ValueError(f"{prefix} 已绑定到 {saved['harness']}")
        path = Path(saved["path"])
        harness = saved["harness"]
        if path.is_file():
            return source_from_path(path, harness, prefix)
    candidates = []
    if harness in {"auto", "antigravity"}:
        candidates.extend(BRAIN.glob(f"{prefix}*/.system_generated/logs/transcript_full.jsonl"))
    if harness in {"auto", "codex"}:
        for root in (CODEX_HOME / "sessions", CODEX_HOME / "archived_sessions"):
            candidates.extend(root.rglob(f"rollout-*{prefix}*.jsonl"))
    sources = [source_from_path(path, harness, prefix) for path in sorted(set(candidates))]
    if len(sources) != 1:
        found = ", ".join(f"{s.harness}:{s.sid}" for s in sources[:5]) or "无匹配"
        raise ValueError(f"会话 {prefix} 需要唯一日志，当前 {found}；请指定 --harness 或 --source")
    return sources[0]


def atomic_write(path, text):
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def source_signature(path):
    stat = path.stat()
    return [str(path), stat.st_mtime_ns, stat.st_size]


def read_json(path):
    value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(value, dict):
        raise ValueError(f"{path}: 状态必须是 JSON 对象")
    return value


def subscribed(directory):
    return directory.is_dir() and not (directory / ".unsubscribed").exists()


def sync_source(source, subscribe=False):
    directory = SESS / source.sid
    directory.mkdir(parents=True, exist_ok=True)
    # Lock before reading to prevent a slow watcher overwriting a newer manual sync.
    with (directory / ".sync.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not subscribe and not subscribed(directory):
            return False
        binding = directory / ".source.json"
        saved = None
        if binding.exists():
            saved = read_json(binding)
            if saved["harness"] != source.harness or saved["sid"] != source.sid:
                raise ValueError(f"{directory} 已绑定到不同来源")
        header = attribution()
        signature = source_signature(source.path)
        records, incomplete_tail = read_snapshot(source.path)
        content = render(source.sid, source.path, source.harness, header, records)
        atomic_write(directory / "prompts.md", content)
        source_metadata = {"sid": source.sid, "harness": source.harness, "path": str(source.path)}
        if saved != source_metadata:
            atomic_write(binding, json.dumps(source_metadata, ensure_ascii=False, indent=2) + "\n")
        try:
            with (directory / "map.md").open("x", encoding="utf-8") as stream:
                stream.write(header + "\n\n" + MAP_TMPL.format(sid8=source.sid[:8]))
        except FileExistsError:
            pass
        parsed = codex_turns(records) if source.harness == "codex" else list(turns(records))
        title = user_text(parsed[0]["user"].get("content", "")) if parsed else ""
        now = datetime.now(TZ).isoformat()
        state = {"source_signature": signature, "last_synced_at": now, "last_attempt_at": now,
                 "title": title.splitlines()[0][:120] if title else source.sid,
                 "turn_count": len(parsed), "last_error": None, "incomplete_tail": incomplete_tail}
        atomic_write(directory / ".sync-state.json", json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        if subscribe:
            (directory / ".unsubscribed").unlink(missing_ok=True)
    return True


def sync(sid_or_prefix, harness="auto", source_path=None, subscribe=True):
    source = resolve_source(sid_or_prefix, harness, source_path)
    sync_source(source, subscribe=subscribe)
    print(f"synced {source.harness}:{source.sid} -> {SESS / source.sid / 'prompts.md'}")
    return True


def sync_all():
    SESS.mkdir(parents=True, exist_ok=True)
    ok = True
    for d in sorted(SESS.glob("*/")):
        if subscribed(d):
            try:
                sync(d.name, subscribe=False)
            except (OSError, ValueError, KeyError) as error:
                print(f"{d.name}: {error}", file=sys.stderr)
                ok = False
    return ok


def watch(interval):
    SESS.mkdir(parents=True, exist_ok=True)
    seen, sources, errors, bindings = {}, {}, {}, {}
    while True:
        heartbeat = {"pid": os.getpid(), "updated_at": datetime.now(TZ).isoformat(),
                     "interval_seconds": interval, "output_root": str(SESS)}
        atomic_write(SESS / ".watcher.json", json.dumps(heartbeat) + "\n")
        for d in SESS.glob("*/"):
            if not subscribed(d):
                seen.pop(d.name, None)
                continue
            try:
                source = sources.get(d.name)
                binding = d / ".source.json"
                binding_stamp = binding.stat().st_mtime_ns if binding.exists() else None
                if source is None or not source.path.exists() or bindings.get(d.name) != binding_stamp:
                    source = resolve_source(d.name)
                    sources[d.name] = source
                    bindings[d.name] = binding_stamp
                signature = source_signature(source.path)
                if seen.get(d.name) != signature or not (d / "prompts.md").exists():
                    sync_source(source)
                    seen[d.name] = signature
                    errors.pop(d.name, None)
            except (OSError, ValueError, KeyError) as error:
                if errors.get(d.name) != str(error):
                    print(f"{d.name}: {error}", file=sys.stderr, flush=True)
                    errors[d.name] = str(error)
                    record_sync_error(d, error)
        active = {d.name for d in SESS.iterdir() if d.is_dir()}
        for mapping in (seen, sources, errors, bindings):
            for sid in set(mapping) - active:
                del mapping[sid]
        time.sleep(interval)


def record_sync_error(directory, error):
    try:
        with (directory / ".sync.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                state = read_json(directory / ".sync-state.json")
            except ValueError:
                state = {}
            state.update(last_attempt_at=datetime.now(TZ).isoformat(), last_error=str(error))
            atomic_write(directory / ".sync-state.json", json.dumps(state, ensure_ascii=False) + "\n")
    except OSError:
        pass


def watcher_status():
    try:
        heartbeat = read_json(SESS / ".watcher.json")
        if not heartbeat:
            return {"status": "unknown", "pid": None}
        pid = int(heartbeat["pid"])
        if pid <= 0:
            raise ValueError("invalid watcher PID")
        try:
            os.kill(pid, 0)
            alive = True
        except ProcessLookupError:
            alive = False
        except PermissionError:
            alive = True
        age = max(0, (datetime.now(TZ) - ts(heartbeat["updated_at"])).total_seconds())
        fresh = age <= max(5, 3 * heartbeat["interval_seconds"])
        status = "stopped"
        if alive:
            status = "running" if fresh else "stale"
        return {**heartbeat, "status": status, "heartbeat_age_seconds": round(age, 2)}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {"status": "unknown", "pid": None, "error": str(error)}


def subscription_directory(prefix):
    validate_id(prefix)
    exact = SESS / prefix
    if exact.is_dir():
        return exact
    matches = [directory for directory in SESS.glob(f"{prefix}*") if directory.is_dir()]
    if len(matches) != 1:
        raise ValueError(f"订阅 {prefix} 匹配 {len(matches)} 个目录，请使用完整 ID")
    return matches[0]


def subscription_info(directory, watcher=None):
    if watcher is None:
        watcher = watcher_status()
    info = {"id": directory.name, "harness": "unknown", "name": directory.name,
            "name_source": "id", "subscribed": subscribed(directory),
            "watching": subscribed(directory) and watcher["status"] == "running",
            "source_path": None, "source_modified_at": None, "last_synced_at": None,
            "last_attempt_at": None, "turn_count": None, "sync_status": "unknown",
            "error": None, "map_path": str(directory / "map.md"),
            "prompts_path": str(directory / "prompts.md")}
    try:
        binding = read_json(directory / ".source.json")
        state = read_json(directory / ".sync-state.json")
        info.update(harness=binding.get("harness", "unknown"),
                    last_synced_at=state.get("last_synced_at"), last_attempt_at=state.get("last_attempt_at"),
                    turn_count=state.get("turn_count"), error=state.get("last_error"))
        if state.get("title"):
            info.update(name=state["title"], name_source="first_prompt")
        if not binding:
            return info
        path = Path(binding["path"])
        info["source_path"] = str(path)
        if not path.exists():
            info["sync_status"] = "source_missing"
        else:
            signature = source_signature(path)
            info["source_modified_at"] = datetime.fromtimestamp(signature[1] / 1e9, TZ).isoformat()
            if info["error"]:
                info["sync_status"] = "error"
            elif not (directory / "prompts.md").exists():
                info["sync_status"] = "output_missing"
            elif state.get("source_signature"):
                complete = state["source_signature"] == signature and not state.get("incomplete_tail")
                info["sync_status"] = "up_to_date" if complete else "pending"
    except (OSError, ValueError, KeyError, TypeError) as error:
        info.update(sync_status="error", error=str(error))
    return info


def unsubscribe(prefix):
    directory = subscription_directory(prefix)
    with (directory / ".sync.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        atomic_write(directory / ".unsubscribed", datetime.now(TZ).isoformat() + "\n")
    return directory


def current_session(harness):
    env_ids = {"codex": os.environ.get("CODEX_THREAD_ID"),
               "antigravity": os.environ.get("ANTIGRAVITY_CONVERSATION_ID")}
    matches = [(kind, sid) for kind, sid in env_ids.items() if sid and harness in {"auto", kind}]
    if len(matches) != 1:
        raise ValueError("无法唯一识别当前会话，请显式指定 --harness 和会话 ID")
    return matches[0]


def manage(argv):
    global SESS
    command = argv[0]
    parser = argparse.ArgumentParser(prog=f"sync.py {command}", description="查询和管理会话订阅")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--harness", choices=("auto", "codex", "antigravity"), default="auto")
    if command == "list":
        parser.add_argument("--all", action="store_true", help="同时列出已退订的会话")
    else:
        parser.add_argument("sid", nargs="?", help="完整会话 ID 或唯一前缀")
        parser.add_argument("--current", action="store_true")
    if command == "subscribe":
        parser.add_argument("--source", type=Path)
    args = parser.parse_args(argv[1:])
    if args.output_root:
        SESS = args.output_root.expanduser().resolve()
    try:
        watcher = watcher_status()
        if command == "list":
            items = [subscription_info(directory, watcher) for directory in sorted(SESS.glob("*/"))
                     if directory.is_dir() and (args.all or subscribed(directory))]
            items = [item for item in items if args.harness in {"auto", item["harness"]}]
            result = {"watcher": watcher, "subscriptions": items}
        else:
            if args.current:
                if args.sid or getattr(args, "source", None):
                    raise ValueError("--current 与 ID / --source 不能同时指定")
                args.harness, args.sid = current_session(args.harness)
            if command == "subscribe":
                source = resolve_source(args.sid, args.harness, args.source)
                sync_source(source, subscribe=True)
                directory = SESS / source.sid
            else:
                if not args.sid:
                    raise ValueError("需要会话 ID 或 --current")
                directory = subscription_directory(args.sid)
                if args.harness != "auto" and subscription_info(directory)["harness"] != args.harness:
                    raise ValueError("订阅的 harness 与请求不符")
                if command == "unsubscribe":
                    unsubscribe(directory.name)
            result = {"watcher": watcher_status(), "subscription": subscription_info(directory)}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"watcher={result['watcher']['status']}")
            items = result.get("subscriptions", [result.get("subscription")])
            for item in items:
                print(f"{item['id']}  {item['harness']}  subscribed={item['subscribed']}  "
                      f"watching={item['watching']}  {item['sync_status']}  {item['name']}")
                if command != "list":
                    print(json.dumps(item, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as error:
        if args.json:
            print(json.dumps({"error": str(error)}, ensure_ascii=False))
        else:
            print(f"error: {error}", file=sys.stderr)
        return 1


def install_service():
    SERVICE_PATH.parent.mkdir(parents=True, exist_ok=True)
    unit = f"""[Unit]
Description=Antigravity and Codex Session Map Watcher ({REPO.name})
After=default.target

[Service]
Type=simple
WorkingDirectory={REPO}
ExecStart=/usr/bin/python3 { Path(__file__).resolve() } --watch
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
"""
    SERVICE_PATH.write_text(unit, encoding="utf-8")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", SERVICE_NAME], check=True)
    subprocess.run(["systemctl", "--user", "restart", SERVICE_NAME], check=True)
    subprocess.run(["systemctl", "--user", "status", "--no-pager", SERVICE_NAME], check=False)


def status_service():
    subprocess.run(["systemctl", "--user", "status", "--no-pager", SERVICE_NAME], check=False)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in {"list", "show", "subscribe", "unsubscribe"}:
        sys.exit(manage(sys.argv[1:]))
    ap = argparse.ArgumentParser(description="session-map 同步与监听工具；支持 list/show/subscribe/unsubscribe 子命令")
    ap.add_argument("sid", nargs="?", help="会话 ID 或前缀 (支持前 8 位)")
    ap.add_argument("--harness", choices=("auto", "antigravity", "codex"), default="auto")
    ap.add_argument("--current", action="store_true", help="从当前 harness 的会话环境变量取得 ID")
    ap.add_argument("--source", type=Path, help="显式指定本地 JSONL 日志")
    ap.add_argument("--output-root", type=Path, help="覆盖归档根目录，用于隔离测试或导出")
    ap.add_argument("--all", action="store_true", help="单次同步全部已订阅会话")
    ap.add_argument("--watch", action="store_true", help="常驻轮询已订阅会话")
    ap.add_argument("-i", "--interval", type=float, default=1.0, help="轮询间隔秒数 (默认 1.0)")
    ap.add_argument("--install-service", action="store_true", help="安装并启动 systemd --user 服务")
    ap.add_argument("--status-service", action="store_true", help="查看 systemd --user 服务状态")
    a = ap.parse_args()
    if a.output_root:
        SESS = a.output_root.expanduser().resolve()
    if a.interval <= 0:
        ap.error("--interval 必须大于 0")
    if a.current:
        if a.sid or a.source:
            ap.error("--current 与 ID / --source 不能同时指定")
        try:
            a.harness, a.sid = current_session(a.harness)
        except ValueError as error:
            ap.error(str(error))
    if a.install_service:
        install_service()
    elif a.status_service:
        status_service()
    elif a.watch:
        watch(a.interval)
    elif a.all:
        sys.exit(0 if sync_all() else 1)
    elif a.sid or a.source:
        try:
            sync(a.sid, a.harness, a.source)
        except (OSError, ValueError, KeyError) as error:
            ap.exit(1, f"error: {error}\n")
    else:
        ap.error("需要 <id>、--all、--watch、--install-service 或 --status-service")
