"""Locate, validate, and read harness logs through symmetric adapters."""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import antigravity
import codex
from models import Source, TZ

BRAIN = Path.home() / ".gemini/antigravity/brain"
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
ADAPTERS = {"codex": codex, "antigravity": antigravity}


def parse_turns(records, harness, assets=None):
    return list(ADAPTERS[harness].parse_turns(records, assets=assets))


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


def read_json(path):
    value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(value, dict):
        raise ValueError(f"{path}: 状态必须是 JSON 对象")
    return value


def validate_id(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{7,}", value):
        raise ValueError("会话 ID 须为至少 8 位的字母、数字、连字符或下划线")


def source_signature(path):
    stat = path.stat()
    return [str(path), stat.st_mtime_ns, stat.st_size]


def current_session(harness):
    env_ids = {"codex": os.environ.get("CODEX_THREAD_ID"),
               "antigravity": os.environ.get("ANTIGRAVITY_CONVERSATION_ID")}
    matches = [(kind, sid) for kind, sid in env_ids.items() if sid and harness in {"auto", kind}]
    if len(matches) != 1:
        raise ValueError("无法唯一识别当前会话，请显式指定 --harness 和会话 ID")
    return matches[0]


def source_from_path(path, harness="auto", prefix=None):
    path = path.expanduser().resolve()
    records = read_records(path)
    actual = next((name for name, adapter in ADAPTERS.items() if adapter.matches(records)), None)
    if actual is None:
        raise ValueError(f"{path}: 未识别到会话元数据或 USER_INPUT")
    if harness not in {"auto", actual}:
        raise ValueError(f"日志格式为 {actual}，与 --harness {harness} 不符")
    sid = ADAPTERS[actual].session_id(records, path)
    validate_id(sid)
    if prefix and not sid.startswith(prefix):
        raise ValueError(f"日志中的会话 {sid} 与请求的 {prefix} 不符")
    return Source(sid, actual, path)


def resolve_source(prefix, harness="auto", source_path=None, *, output_root):
    if prefix:
        validate_id(prefix)
    if source_path:
        return source_from_path(source_path, harness, prefix)
    if not prefix:
        raise ValueError("需要会话 ID、--current 或 --source")
    metadata = output_root / prefix / ".source.json"
    if metadata.exists():
        saved = read_json(metadata)
        if harness not in {"auto", saved["harness"]}:
            raise ValueError(f"{prefix} 已绑定到 {saved['harness']}")
        path = Path(saved["path"])
        harness = saved["harness"]
        if path.is_file():
            return source_from_path(path, harness, prefix)
    candidates = []
    roots = {"antigravity": BRAIN, "codex": CODEX_HOME}
    for name, adapter in ADAPTERS.items():
        if harness in {"auto", name}:
            candidates.extend(adapter.find_paths(roots[name], prefix))
    sources = [source_from_path(path, harness, prefix) for path in sorted(set(candidates))]
    if len(sources) != 1:
        found = ", ".join(f"{s.harness}:{s.sid}" for s in sources[:5]) or "无匹配"
        raise ValueError(f"会话 {prefix} 需要唯一日志，当前 {found}；请指定 --harness 或 --source")
    return sources[0]


def attribution(source, repo):
    script = repo / ".agents/skills/get-model-name/scripts/get_model_name.py"
    command = [sys.executable, str(script), "--header", "--framework", source.harness]
    env = dict(os.environ)
    # A watcher may be launched by a different agent. Attribute the bound source,
    # never an inherited model override or the process that runs the export.
    env.pop("AI_MODEL_NAME", None)
    if source.harness == "codex":
        env["CODEX_THREAD_ID"] = source.sid
        command.extend(["--session-log", str(source.path)])
    else:
        env["ANTIGRAVITY_CONVERSATION_ID"] = source.sid
        env["ANTIGRAVITY_APP_DATA_DIR"] = str(source.path.parents[4])
        command.extend(["--session-id", source.sid])
    try:
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=20, check=True)
        if all(f"- {key}:" in result.stdout for key in ("agent name", "harness", "session", "time")):
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return (f"- agent name: unknown\n- harness: {source.harness}\n- session: {source.sid[:8]}\n"
            f"- time: {datetime.now(TZ):%Y-%m-%d %H:%M} (Asia/Shanghai)")

