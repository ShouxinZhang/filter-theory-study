#!/usr/bin/env python3
"""输出当前 AI 编程模型标识；无法核实时输出 ``unknown``。"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from contextlib import closing
from collections import deque
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

UNKNOWN = "unknown"
FRAMEWORKS = (
    "codex",
    "github-copilot",
    "github-copilot-vscode",
    "claude-code",
    "opencode",
    "grok",
)


class ChineseArgumentParser(argparse.ArgumentParser):
    """将 argparse 帮助标题统一为简体中文。"""

    def format_help(self) -> str:
        return (
            super()
            .format_help()
            .replace("usage:", "用法:", 1)
            .replace("options:", "选项:", 1)
        )


def clean_model(value: Any) -> str | None:
    """接受模型标识，拒绝不代表具体模型的选择器。"""
    if not isinstance(value, str):
        return None
    model = value.strip()
    if not model or any(c.isspace() for c in model) or model.lower() in {"auto", "default", "unknown", "<synthetic>"}:
        return None
    return model


def json_lines(path: Path) -> Iterable[dict[str, Any]]:
    """逐行读取合法 JSON，并容忍未写完的会话日志行。"""
    try:
        with path.open(encoding="utf-8", errors="replace") as stream:
            for line in stream:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    yield value
    except OSError:
        return


def last_match(
    path: Path, extract: Callable[[dict[str, Any]], str | None]
) -> str | None:
    """返回最后一个匹配值，不在内存中保留完整日志。"""
    matches: deque[str] = deque(maxlen=1)
    for item in json_lines(path):
        model = extract(item)
        if model:
            matches.append(model)
    return matches[-1] if matches else None


def newest(paths: Iterable[Path]) -> Path | None:
    """选择最近修改且可读取的路径。"""
    candidates: list[tuple[int, Path]] = []
    for path in paths:
        try:
            candidates.append((path.stat().st_mtime_ns, path))
        except OSError:
            continue
    return max(candidates, default=(0, None))[1]


def model_from_mapping(value: Any) -> str | None:
    """将常见供应商/模型对象规范化为稳定标识。"""
    if isinstance(value, str):
        return clean_model(value)
    if not isinstance(value, dict):
        return None
    model = clean_model(
        value.get("modelID")
        or value.get("model_id")
        or value.get("id")
        or value.get("name")
    )
    provider = clean_model(
        value.get("providerID") or value.get("provider_id") or value.get("provider")
    )
    if model and provider and not model.startswith(f"{provider}/"):
        return f"{provider}/{model}"
    return model


def valid_session_id(value: str | None) -> bool:
    return bool(value) and all(c.isalnum() or c in "-_" for c in value)


def codex_model(env: dict[str, str]) -> str | None:
    """从当前 Codex 回合上下文读取实际模型。"""
    thread_id = env.get("CODEX_THREAD_ID")
    if not valid_session_id(thread_id):
        return None
    root = Path(env.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
    session = newest(root.glob(f"sessions/**/*-{thread_id}.jsonl"))
    if not session:
        return None

    def extract(item: dict[str, Any]) -> str | None:
        if item.get("type") != "turn_context":
            return None
        payload = item.get("payload")
        return (clean_model(payload.get("model")) or UNKNOWN) if isinstance(payload, dict) else UNKNOWN

    return last_match(session, extract)


def copilot_model(env: dict[str, str]) -> str | None:
    """从 Copilot 会话开始或最后一次模型切换事件读取模型。"""
    root = Path(env.get("COPILOT_HOME", str(Path.home() / ".copilot"))).expanduser()
    session_id = env.get("COPILOT_SESSION_ID")
    if valid_session_id(session_id):
        event_file = root / "session-state" / session_id / "events.jsonl"
    else:
        return None

    def extract(item: dict[str, Any]) -> str | None:
        if item.get("type") not in {
            "session.start",
            "session.resume",
            "session.model_change",
        }:
            return None
        data = item.get("data")
        if not isinstance(data, dict):
            return UNKNOWN
        for key in ("resolvedModel", "newModel", "model", "modelId", "model_id"):
            if key in data:
                return model_from_mapping(data[key]) or UNKNOWN
        return UNKNOWN

    session_model = (
        last_match(event_file, extract) if event_file and event_file.is_file() else None
    )
    return session_model


def replay_mutation_log(path: Path) -> Any:
    """重放 VS Code 聊天会话增量日志（kind 0 全量、1 赋值、2 追加、3 删除）。"""
    state: Any = None
    for item in json_lines(path):
        kind = item.get("kind")
        if kind == 0:
            state = item.get("v")
            continue
        keys = item.get("k")
        if state is None or not isinstance(keys, list) or not keys:
            continue
        target = state
        try:
            for key in keys[:-1]:
                target = target[key]
            last = keys[-1]
            if kind == 1:
                target[last] = item.get("v")
            elif kind == 2:
                array = target[last]
                if not isinstance(array, list):
                    continue
                index = item.get("i")
                if isinstance(index, int):
                    del array[index:]
                values = item.get("v")
                if isinstance(values, list):
                    array.extend(values)
            elif kind == 3:
                del target[last]
        except (KeyError, IndexError, TypeError):
            continue
    return state


def vscode_session_file(env: dict[str, str], session_log: str | None) -> Path | None:
    """由 VSCODE_TARGET_SESSION_LOG 定位 workspaceStorage/<ws>/chatSessions/<sid>.jsonl。"""
    raw = session_log or env.get("VSCODE_TARGET_SESSION_LOG")
    if not raw:
        return None
    log_dir = Path(raw).expanduser()
    session_id = log_dir.name
    if not valid_session_id(session_id) or log_dir.parent.name != "debug-logs":
        return None
    workspace = log_dir.parent.parent.parent
    candidate = workspace / "chatSessions" / f"{session_id}.jsonl"
    return candidate if candidate.is_file() else None


def copilot_vscode_model(env: dict[str, str], session_log: str | None = None) -> str | None:
    """从 VS Code Copilot Chat 当前会话最后一个请求读取模型。"""
    session = vscode_session_file(env, session_log)
    if not session:
        return None
    state = replay_mutation_log(session)
    if not isinstance(state, dict):
        return None
    requests = state.get("requests")
    if not isinstance(requests, list) or not requests or not isinstance(requests[-1], dict):
        return None
    request = requests[-1]
    result = request.get("result")
    metadata = result.get("metadata") if isinstance(result, dict) else None
    if isinstance(metadata, dict):
        resolved = clean_model(metadata.get("resolvedModel"))
        if resolved:
            return resolved
    selected_id = request.get("modelId")
    if not isinstance(selected_id, str):
        return UNKNOWN
    # 请求尚未完成时，用选中模型元数据把 vendor/group/id 标识换成模型 id。
    selected = (state.get("inputState") or {}).get("selectedModel")
    if isinstance(selected, dict) and selected.get("identifier") == selected_id:
        info = selected.get("metadata")
        if isinstance(info, dict):
            model = clean_model(info.get("id"))
            if model:
                return model
    tail = selected_id.rsplit("/", 1)[-1]
    if clean_model(tail) is None:  # 如 copilot/auto：后端尚未解析
        return UNKNOWN
    return clean_model(selected_id) or UNKNOWN


def claude_model(env: dict[str, str]) -> str | None:
    """从 Claude Code 最近一条助手消息读取模型。"""
    root = Path(env.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))).expanduser()
    session_id = env.get("CLAUDE_CODE_SESSION_ID") or env.get("CLAUDE_SESSION_ID")
    if valid_session_id(session_id):
        transcript = newest(root.glob(f"projects/**/{session_id}.jsonl"))
    else:
        return None
    if not transcript:
        return None

    def extract(item: dict[str, Any]) -> str | None:
        message = item.get("message")
        if item.get("type") != "assistant":
            return None
        return (clean_model(message.get("model")) or UNKNOWN) if isinstance(message, dict) else UNKNOWN

    return last_match(transcript, extract)


def opencode_model(env: dict[str, str], cwd: Path) -> str | None:
    """从 OpenCode 只读会话数据库读取选中模型。"""
    data_root = Path(
        env.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))
    ).expanduser()
    database = Path(
        env.get("OPENCODE_DB", str(data_root / "opencode/opencode.db"))
    ).expanduser()
    session_id = env.get("OPENCODE_SESSION_ID")
    if not valid_session_id(session_id) or not database.is_file():
        return None
    try:
        with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            row = connection.execute(
                "SELECT model FROM session WHERE id = ?", (session_id,)
            ).fetchone()
    except (OSError, sqlite3.Error):
        return None
    if row and row[0]:
        try:
            return model_from_mapping(json.loads(row[0]))
        except (TypeError, json.JSONDecodeError):
            return clean_model(row[0])
    return None


def grok_model(env: dict[str, str], cwd: Path) -> str | None:
    """从 Grok 会话摘要读取当前模型标识。"""
    root = Path(env.get("GROK_HOME", str(Path.home() / ".grok"))).expanduser()
    session_id = env.get("GROK_SESSION_ID")
    if not valid_session_id(session_id):
        return None
    summary = newest(root.glob(f"sessions/**/{session_id}/summary.json"))
    if summary:
        try:
            data = json.loads(summary.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return clean_model(data.get("current_model_id"))
        except (OSError, json.JSONDecodeError):
            pass
    return None


def parent_commands() -> str:
    """仅检查进程名称，用于识别调用方框架。"""
    commands: list[str] = []
    pid = os.getppid()
    for _ in range(12):
        if pid <= 1:
            break
        try:
            commands.append(
                Path(f"/proc/{pid}/comm").read_text(encoding="utf-8").strip().lower()
            )
            status = Path(f"/proc/{pid}/status").read_text(
                encoding="utf-8", errors="ignore"
            )
            pid = int(
                next(
                    line.split()[1]
                    for line in status.splitlines()
                    if line.startswith("PPid:")
                )
            )
        except (OSError, StopIteration, ValueError):
            break
    return "\n".join(commands)


def infer_framework(env: dict[str, str]) -> str | None:
    """识别当前宿主，不使用过期模型历史推断。"""
    explicit = env.get("AI_FRAMEWORK")
    if explicit in FRAMEWORKS:
        return explicit
    if env.get("AI_AGENT") == "github_copilot_vscode_agent" or env.get(
        "VSCODE_TARGET_SESSION_LOG"
    ):
        return "github-copilot-vscode"
    markers = (
        ("codex", ("CODEX_THREAD_ID",)),
        ("github-copilot", ("COPILOT_CLI", "COPILOT_SESSION_ID", "COPILOT_MODEL")),
        ("opencode", ("OPENCODE_PID", "OPENCODE_SESSION_ID")),
        ("grok", ("GROK_SESSION_ID", "GROK_HOOK_EVENT")),
        ("claude-code", ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID")),
    )
    for framework, names in markers:
        if any(env.get(name) for name in names):
            return framework
    commands = parent_commands()
    for framework, command in (
        ("codex", "codex"),
        ("github-copilot", "copilot"),
        ("claude-code", "claude"),
        ("opencode", "opencode"),
        ("grok", "grok"),
    ):
        if command in commands.splitlines():
            return framework
    return None


def main() -> int:
    """解析当前框架，仅输出一个可审计值。"""
    parser = ChineseArgumentParser(description=__doc__, add_help=False)
    parser.add_argument("-h", "--help", action="help", help="显示帮助并退出")
    parser.add_argument(
        "--framework", choices=FRAMEWORKS, help="显式指定当前 AI 编程框架"
    )
    parser.add_argument(
        "--session-log",
        help="VS Code Copilot Chat 的 VSCODE_TARGET_SESSION_LOG（debug-logs/<会话 ID> 目录）",
    )
    args = parser.parse_args()
    env = dict(os.environ)
    explicit_model = clean_model(env.get("AI_MODEL_NAME"))
    if "AI_MODEL_NAME" in env:
        print(explicit_model or UNKNOWN)
        return 0
    framework = args.framework or (
        "github-copilot-vscode" if args.session_log else infer_framework(env)
    )
    cwd = Path.cwd().resolve()
    detectors: dict[str, Callable[[], str | None]] = {
        "codex": lambda: codex_model(env),
        "github-copilot": lambda: copilot_model(env),
        "github-copilot-vscode": lambda: copilot_vscode_model(env, args.session_log),
        "claude-code": lambda: claude_model(env),
        "opencode": lambda: opencode_model(env, cwd),
        "grok": lambda: grok_model(env, cwd),
    }
    model = detectors[framework]() if framework in detectors else None
    print(model or UNKNOWN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
