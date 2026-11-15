"""Adapt local Claude Code transcripts to session-map's renderable turns."""

import json
import re

from models import TurnParser

INTERRUPTED = "[Request interrupted by user"
# Host-injected envelopes are transport metadata, not user prose.
INJECTED = re.compile(
    r"<(system-reminder|local-command-stdout|local-command-stderr|local-command-caveat)>.*?</\1>\s*",
    re.DOTALL,
)
SESSION_FILE = re.compile(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}")
# Claude Code tools mapped onto the names the shared renderer already formats.
TOOL_NAMES = {"Bash": "run_command", "Write": "write_file", "Edit": "edit_file", "Read": "read_file"}


def conversational(record):
    return (record.get("type") in {"user", "assistant"} and record.get("sessionId")
            and isinstance(record.get("message"), dict))


def matches(records):
    return any(conversational(record) for record in records)


def session_id(records, path):
    """Prefer the file name; resumed sessions can carry records from an earlier ID."""
    if SESSION_FILE.fullmatch(path.stem):
        return path.stem
    return next(record["sessionId"] for record in records if conversational(record))


def find_paths(root, prefix):
    # Subagent transcripts live one level deeper and are intentionally skipped.
    return root.glob(f"projects/*/{prefix}*.jsonl")


def image_text(block, assets=None):
    source = block.get("source") or {}
    data, mime = source.get("data"), source.get("media_type")
    if assets and source.get("type") == "base64" and isinstance(data, str) and mime:
        path, refs = assets.extract(f"data:{mime};base64,{data}")
        if refs:
            return f"![图像附件]({path})"
    return "[图像附件]"


def text_content(content, assets=None):
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif block.get("type") == "image":
            parts.append(image_text(block, assets))
    return "\n\n".join(parts)


def prompt_text(content, assets=None):
    return INJECTED.sub("", text_content(content, assets)).strip()


def result_text(block):
    """Keep image payloads as data URIs so the shared asset store externalizes them."""
    content = block.get("content", "")
    if isinstance(content, str):
        return content
    parts = []
    for item in content or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text":
            parts.append(item.get("text", ""))
        elif item.get("type") == "image":
            source = item.get("source") or {}
            if source.get("type") == "base64" and source.get("data") and source.get("media_type"):
                parts.append(f"data:{source['media_type']};base64,{source['data']}")
            else:
                parts.append("[图像附件]")
        else:
            parts.append(json.dumps(item, ensure_ascii=False, indent=2))
    return "\n\n".join(parts)


def tool_call(block):
    name, args = block.get("name", "tool"), block.get("input")
    if not isinstance(args, dict):
        args = {"input": args}
    if name == "Bash":
        args = {"CommandLine": args.get("command", ""), "toolSummary": args.get("description")}
    elif name == "Write":
        args = {"Path": args.get("file_path", ""), "Content": args.get("content", "")}
    elif name == "Edit":
        args = {"Path": args.get("file_path", ""), "Target": args.get("old_string", ""),
                "Replacement": args.get("new_string", "")}
    elif name == "Read":
        args = {"Path": args.get("file_path", ""),
                **{key: value for key, value in args.items() if key != "file_path"}}
    return {"name": TOOL_NAMES.get(name, name), "args": args, "pending": True}


class Parser(TurnParser):
    def __init__(self, assets=None, **hints):
        super().__init__(assets, **hints)
        self.calls, self.call_ids, self.seen = {}, set(), set()
        self.current = None

    def append(self, step):
        self.touch(self.current)["steps"].append(step)

    def accept(self, record):
        if not conversational(record) or record.get("isSidechain") or record.get("isMeta"):
            return
        uuid = record.get("uuid")
        if uuid:
            # Resumed sessions replay earlier records under the same uuid.
            if uuid in self.seen:
                return
            self.seen.add(uuid)
        timestamp = record.get("timestamp", "")
        message = record["message"]
        content = message.get("content")
        blocks = content if isinstance(content, list) else []
        if record["type"] == "user":
            self.accept_user(record, content, blocks, timestamp)
        elif self.current is not None:
            self.accept_assistant(message, blocks, timestamp)

    def accept_user(self, record, content, blocks, timestamp):
        outputs = [block for block in blocks
                   if isinstance(block, dict) and block.get("type") == "tool_result"]
        for block in outputs:
            call_id = block.get("tool_use_id")
            if call_id in self.calls:
                # Only unanswered calls stay referenced; answered ones are released.
                call, owner = self.calls.pop(call_id)
                self.touch(owner)
                call.update(result=result_text(block), pending=False)
            elif call_id not in self.call_ids and self.current is not None:
                self.append({
                    "type": "PLANNER_RESPONSE", "created_at": timestamp,
                    "content": "工具输出（源日志未包含对应调用）", "phase": "commentary",
                    "tool_calls": [{"name": "tool_output", "args": {},
                                    "result": result_text(block)}],
                })
        if outputs:
            if self.current is not None:
                self.touch(self.current)["last_activity_at"] = timestamp
            return
        text = prompt_text(content, self.assets)
        if not text:
            return
        if text.startswith(INTERRUPTED):
            if self.current is not None:
                self.touch(self.current).update(status="interrupted", ended_at=timestamp)
            return
        origin = (record.get("origin") or {}).get("kind", "human")
        if record.get("isCompactSummary") or origin != "human":
            # Compaction summaries and host notifications are not human prompts.
            if self.current is not None:
                note = ("[上下文已压缩，原始记录以本地日志保留范围为准]"
                        if record.get("isCompactSummary") else text)
                self.append({"type": "PLANNER_RESPONSE", "created_at": timestamp,
                             "content": note, "phase": "commentary"})
            return
        if self.current is not None and self.current["status"] == "working":
            self.touch(self.current)["status"] = "completed"
        self.current = self.open_turn({"user": {"content": text, "created_at": timestamp},
                                       "steps": [], "status": "working"})

    def accept_assistant(self, message, blocks, timestamp):
        finished = message.get("stop_reason") == "end_turn"
        narration = message.get("stop_reason") == "tool_use"
        for block in blocks:
            if not isinstance(block, dict):
                continue
            step = {"type": "PLANNER_RESPONSE", "created_at": timestamp}
            kind = block.get("type")
            if kind == "text":
                if not block.get("text", "").strip():
                    continue
                step.update(content=block["text"], phase="commentary" if narration else "final")
            elif kind == "thinking":
                # Only the displayed thinking text; signatures and redacted blocks stay local.
                if not block.get("thinking", "").strip():
                    continue
                step.update(thinking=block["thinking"], thought_label="Thinking", phase="commentary")
            elif kind == "tool_use":
                call = tool_call(block)
                if block.get("id"):
                    self.call_ids.add(block["id"])
                    self.calls[block["id"]] = (call, self.current)
                step.update(tool_calls=[call], phase="commentary")
            else:
                continue
            self.append(step)
        current = self.touch(self.current)
        current["status"] = "completed" if finished else "working"
        current["ended_at" if finished else "last_activity_at"] = timestamp
        if not finished:
            current.pop("ended_at", None)


def parse_turns(records, assets=None):
    parser = Parser(assets)
    parser.feed(records)
    return parser.turns
