"""Subscription lifecycle, atomic persistence, and background synchronization."""
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from assets import AssetStore
from models import Source, TZ, ts
from memory import ensure_memory
from map_layout import ensure_map, map_path
from render import user_text
import render as renderer
import sources
from sources import read_json, read_records, read_snapshot, source_signature, validate_id

REPO = Path(__file__).resolve()
while REPO != REPO.parent and not (REPO / ".git").exists():
    REPO = REPO.parent
SESS = REPO / ".agents/.tmp/session"
SERVICE_NAME = "session-map-sync.service"
SERVICE_PATH = Path.home() / ".config/systemd/user" / SERVICE_NAME
ENTRYPOINT = Path(__file__).with_name("sync.py")


def resolve_source(prefix, harness="auto", source_path=None):
    return sources.resolve_source(prefix, harness, source_path, output_root=SESS)


def attribution(source):
    return sources.attribution(source, REPO)


def render(sid, src, harness="antigravity", header=None, records=None, assets=None):
    """Coordinate parsing and rendering; the renderer itself performs no log reads."""
    if records is None:
        records = read_records(src)
    turns = sources.parse_turns(records, harness, assets=assets)
    return renderer.render(sid, src, harness, header or attribution(Source(sid, harness, src)),
                           turns, assets=assets)


def atomic_write(path, text):
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return True


def write_prompts(path, content):
    # Attribution time alone must not make an unchanged transcript reload in VS Code.
    def substantive(text):
        return re.sub(r"^- time:.*$", "- time:", text, count=1, flags=re.MULTILINE)
    if path.exists() and substantive(path.read_text(encoding="utf-8")) == substantive(content):
        return False
    return atomic_write(path, content)


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
        header = attribution(source)
        signature = source_signature(source.path)
        records, incomplete_tail = read_snapshot(source.path)
        content = render(source.sid, source.path, source.harness, header, records,
                         assets=AssetStore(directory))
        write_prompts(directory / "prompts.md", content)
        source_metadata = {"sid": source.sid, "harness": source.harness, "path": str(source.path)}
        if saved != source_metadata:
            atomic_write(binding, json.dumps(source_metadata, ensure_ascii=False, indent=2) + "\n")
        ensure_map(directory, header, source.sid)
        ensure_memory(directory, header)
        parsed = sources.parse_turns(records, source.harness)
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
            "error": None, "map_path": str(map_path(directory)),
            "prompts_path": str(directory / "prompts.md"),
            "memory_path": str(directory / "memory/memory.md"),
            "memory_drafts_path": str(directory / "memory/agent-memory-drafts.md"),
            "memory_references_path": str(directory / "memory/references")}
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


def install_service():
    SERVICE_PATH.parent.mkdir(parents=True, exist_ok=True)
    unit = f"""[Unit]
Description=Antigravity and Codex Session Map Watcher ({REPO.name})
After=default.target

[Service]
Type=simple
WorkingDirectory={REPO}
ExecStart=/usr/bin/python3 {ENTRYPOINT} --watch
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

