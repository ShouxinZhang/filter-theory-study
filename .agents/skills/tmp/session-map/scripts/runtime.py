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
from models import Restart, Source, TZ, pending, ts
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


GUARD_BYTES = 64
HEADER_SECONDS = 60


class Live:
    """In-memory progress of one source: parser state, rendered turns, and read offset."""

    def __init__(self, source, directory, hints=None):
        self.source = source
        self.hints = dict(hints or {})
        self.assets = AssetStore(directory)
        self.parser = sources.new_parser(source.harness, self.assets, **self.hints)
        self.bodies, self.unsealed = [], set()
        self.offset = self.lines = 0
        self.guard, self.identity = b"", None
        self.header, self.header_at = None, 0.0

    def continues(self, stream):
        """Whether the log is still the file this state was read from, only appended to."""
        status = os.fstat(stream.fileno())
        if self.identity is None:
            self.identity = (status.st_dev, status.st_ino)
            return True
        if self.identity != (status.st_dev, status.st_ino) or status.st_size < self.offset:
            return False
        stream.seek(self.offset - len(self.guard))
        return stream.read(len(self.guard)) == self.guard

    def advance(self):
        """Feed appended records, re-render changed turns, and release finished ones."""
        with self.source.path.open("rb") as stream:
            if not self.continues(stream):
                raise Restart()
            stream.seek(self.offset)
            done = False
            while not done:
                records, consumed, lines, incomplete, done = sources.read_batch(
                    stream, self.source.path, self.lines)
                self.parser.feed(records)
                self.refresh()
                self.offset += consumed
                self.lines += lines
            start = max(0, self.offset - GUARD_BYTES)
            stream.seek(start)
            self.guard = stream.read(self.offset - start)
        return incomplete

    def refresh(self):
        parser = self.parser
        for index in sorted(parser.dirty):
            body = renderer.render_turn(index + 1, parser.turns[index], self.assets)
            if index < len(self.bodies):
                self.bodies[index] = body
            else:
                self.bodies.append(body)
                self.unsealed.add(index)
        parser.dirty.clear()
        if self.hints.get("seal", True):
            # Rendered turns that can no longer change keep only their title.
            last = len(parser.turns) - 1
            for index in [i for i in self.unsealed if i != last and not pending(parser.turns[i])]:
                parser.seal(index)
                self.unsealed.discard(index)

    def attribution(self):
        if self.header is None or time.monotonic() - self.header_at > HEADER_SECONDS:
            self.header, self.header_at = attribution(self.source), time.monotonic()
        return self.header


def advance(source, directory, cache):
    """Return an up-to-date Live, reusing cached progress when the log only grew."""
    live = cache.get(source.sid) if cache is not None else None
    if live is not None and live.source != source:
        live = None
    hints = dict(live.hints) if live else {}
    for _ in range(4):
        live = live or Live(source, directory, hints)
        try:
            incomplete = live.advance()
        except Restart as restart:
            if cache is not None:
                cache.pop(source.sid, None)
            if restart.hints and all(hints.get(key) == value for key, value in restart.hints.items()):
                break
            hints.update(restart.hints)
            live = None
            continue
        except BaseException:
            # A partly fed parser is unusable; the next attempt rebuilds from the start.
            if cache is not None:
                cache.pop(source.sid, None)
            raise
        if cache is not None:
            cache[source.sid] = live
        return live, incomplete
    raise ValueError(f"{source.path}: 无法稳定解析日志")


def sync_source(source, subscribe=False, cache=None):
    """Sync one source. With `cache`, later calls read only what was appended."""
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
        signature = source_signature(source.path)
        live, incomplete_tail = advance(source, directory, cache)
        header = live.attribution()
        turns = live.parser.turns
        content = renderer.assemble(source.sid, source.path, source.harness, header, turns, live.bodies)
        write_prompts(directory / "prompts.md", content)
        source_metadata = {"sid": source.sid, "harness": source.harness, "path": str(source.path)}
        if saved != source_metadata:
            atomic_write(binding, json.dumps(source_metadata, ensure_ascii=False, indent=2) + "\n")
        ensure_map(directory, header, source.sid)
        ensure_memory(directory, header)
        title = user_text(turns[0]["user"].get("content", "")) if turns else ""
        now = datetime.now(TZ).isoformat()
        state = {"source_signature": signature, "last_synced_at": now, "last_attempt_at": now,
                 "title": title.splitlines()[0][:120] if title else source.sid,
                 "turn_count": len(turns), "last_error": None, "incomplete_tail": incomplete_tail}
        atomic_write(directory / ".sync-state.json", json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        if subscribe:
            (directory / ".unsubscribed").unlink(missing_ok=True)
    return True


def synced_signature(directory):
    """Signature of the last complete sync, so a restarted watcher skips unchanged logs."""
    try:
        state = read_json(directory / ".sync-state.json")
    except (OSError, ValueError):
        return None
    if state.get("last_error") or state.get("incomplete_tail") or not (directory / "prompts.md").exists():
        return None
    return state.get("source_signature")


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
    seen, sources, errors, bindings, cache = {}, {}, {}, {}, {}
    while True:
        heartbeat = {"pid": os.getpid(), "updated_at": datetime.now(TZ).isoformat(),
                     "interval_seconds": interval, "output_root": str(SESS)}
        atomic_write(SESS / ".watcher.json", json.dumps(heartbeat) + "\n")
        for d in SESS.glob("*/"):
            if not subscribed(d):
                seen.pop(d.name, None)
                cache.pop(d.name, None)
                continue
            if d.name not in seen:
                seen[d.name] = synced_signature(d)
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
                    sync_source(source, cache=cache)
                    seen[d.name] = signature
                    errors.pop(d.name, None)
            except (OSError, ValueError, KeyError) as error:
                if errors.get(d.name) != str(error):
                    print(f"{d.name}: {error}", file=sys.stderr, flush=True)
                    errors[d.name] = str(error)
                    record_sync_error(d, error)
        active = {d.name for d in SESS.iterdir() if d.is_dir()}
        for mapping in (seen, sources, errors, bindings, cache):
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
Description=Session Map Watcher ({REPO.name})
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

