"""Adapt local Codex rollout records to session-map's renderable turns."""

import json
import re

from models import Restart, TurnParser


def matches(records):
    return any(record.get("type") == "session_meta" for record in records)


def session_id(records, path):
    return next(record.get("payload", {}).get("id", "") for record in records
                if record.get("type") == "session_meta")


def find_paths(root, prefix):
    for folder in (root / "sessions", root / "archived_sessions"):
        yield from folder.rglob(f"rollout-*{prefix}*.jsonl")


def text_content(content, assets=None):
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if block.get("type") in {"input_text", "output_text", "text", "summary_text"}:
            parts.append(block.get("text", ""))
        elif block.get("type") in {"input_image", "image"}:
            url = block.get("image_url", "")
            if assets and isinstance(url, str) and url.startswith("data:"):
                path, refs = assets.extract(url)
                parts.append(f"![图像附件]({path})" if refs else "[图像附件]")
            elif assets and isinstance(url, str) and (path := assets.image_path(url)):
                parts.append(f"![图像附件]({path})")
            else:
                parts.append("[图像附件]")
    return "\n\n".join(parts)


def prompt_text(content, assets=None):
    """Exclude host-injected context while retaining actual user text."""
    parts = []
    for block in content or []:
        text = text_content([block], assets).strip()
        if text.startswith("# AGENTS.md instructions for "):
            continue
        if re.fullmatch(
            r"<(environment_context|external_codex_apps_open_page)>.*</\1>",
            text,
            re.DOTALL,
        ):
            continue
        if text:
            parts.append(text)
    text = "\n\n".join(parts)
    if text.startswith("# Files mentioned by the user:") and "## My request:\n" in text:
        text = text.split("## My request:\n", 1)[1]
        # Codex's attachment envelope is transport metadata, not user prose.
        opening = r'^<image name=[^\n]+ path="[^"\n]+">\s*$'
        if re.search(opening, text, re.MULTILINE):
            text = re.sub(opening, "", text, flags=re.MULTILINE)
            text = re.sub(r"^</image>\s*$", "", text, flags=re.MULTILINE)
    return text.strip()



def output_text(value):
    if isinstance(value, list) and all(isinstance(block, dict) and block.get("type") in
                                      {"input_text", "output_text", "text"} for block in value):
        return text_content(value)
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)


class Parser(TurnParser):
    """Resumable rollout parser; `roles` records which Responses items are canonical."""

    def __init__(self, assets=None, **hints):
        super().__init__(assets, **hints)
        # Rollouts can contain UI events and Responses items for the same message.
        # Responses items are canonical when available, including on Desktop.
        self.roles = set(hints.get("roles") or ())
        self.event_roles = set()
        self.calls, self.call_ids, self.seen_items = {}, set(), set()
        self.current, self.active_turn_id = None, None
        self.by_turn_id = {}

    def feed(self, records):
        found = {record.get("payload", {}).get("role") for record in records
                 if record.get("type") == "response_item"}
        new = found - self.roles
        self.roles |= found
        if new & self.event_roles:
            # Earlier batches already used UI events for a role that has Responses items.
            raise Restart(roles=sorted(role for role in self.roles if role))
        super().feed(records)

    def start_prompt(self, text, timestamp):
        self.current = self.open_turn({
            "user": {"content": text, "created_at": timestamp},
            "steps": [],
            "status": "working",
        })
        if self.active_turn_id:
            self.by_turn_id[self.active_turn_id] = self.current

    def append(self, step):
        self.touch(self.current)["steps"].append(step)

    def accept(self, record):
        payload = record.get("payload") or {}
        kind = payload.get("type")
        timestamp = record.get("timestamp", "")
        if record.get("type") == "event_msg":
            if kind == "task_started":
                self.active_turn_id = payload.get("turn_id")
            elif kind == "user_message" and "user" not in self.roles:
                self.event_roles.add("user")
                self.start_prompt(payload.get("message", ""), timestamp)
            elif kind == "agent_message" and "assistant" not in self.roles and self.current:
                self.event_roles.add("assistant")
                self.append({
                    "type": "PLANNER_RESPONSE", "created_at": timestamp,
                    "content": payload.get("message", ""), "phase": "final",
                })
            elif kind in {"task_complete", "turn_aborted"}:
                target = self.by_turn_id.get(payload.get("turn_id"), self.current)
                if target is not None:
                    self.touch(target)
                    target["status"] = "completed" if kind == "task_complete" else "interrupted"
                    target["ended_at"] = timestamp
                    if payload.get("duration_ms") is not None:
                        target["duration_seconds"] = max(0, int(payload["duration_ms"] / 1000))
                    final = payload.get("last_agent_message")
                    if final and not any(step.get("content") == final for step in target["steps"]):
                        target["steps"].append({
                            "type": "PLANNER_RESPONSE", "created_at": timestamp,
                            "content": final, "phase": "final",
                        })
            # item_completed mirrors response items. Raw reasoning in UI events
            # is deliberately outside this exporter; only public summaries below.
            return

        if record.get("type") == "compacted" and self.current:
            self.append({
                "type": "PLANNER_RESPONSE", "created_at": timestamp,
                "content": "[上下文已压缩，原始记录以本地日志保留范围为准]",
                "phase": "commentary",
            })
        if record.get("type") != "response_item":
            return
        item_id = payload.get("id")
        if item_id:
            if item_id in self.seen_items:
                return
            self.seen_items.add(item_id)
        if kind == "message" and payload.get("role") == "user":
            text = prompt_text(payload.get("content"), self.assets)
            if text:
                self.start_prompt(text, timestamp)
            return
        if self.current is None:
            return
        step = {"type": "PLANNER_RESPONSE", "created_at": timestamp}
        if kind == "message" and payload.get("role") == "assistant":
            phase = payload.get("phase") or payload.get("channel")
            if phase in {"analysis", "justify", "confidence"}:
                return
            step.update(content=text_content(payload.get("content"), self.assets), phase=phase or "final")
        elif kind == "reasoning":
            summary = text_content(payload.get("summary"))
            if not summary:
                return
            step.update(thinking=summary, thought_label="Reasoning summary", phase="commentary")
        elif kind in {"function_call", "custom_tool_call"}:
            call_id = payload.get("call_id") or item_id
            if call_id in self.call_ids:
                return
            arguments = payload.get("arguments", payload.get("input", ""))
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except ValueError:
                    arguments = {"input": arguments}
            if not isinstance(arguments, dict):
                arguments = {"input": arguments}
            call = {"name": payload.get("name", "tool"), "args": arguments, "pending": True}
            if call_id:
                # Only unanswered calls stay referenced; answered ones are released.
                self.call_ids.add(call_id)
                self.calls[call_id] = (call, self.current)
            step.update(tool_calls=[call], phase="commentary")
        elif kind in {"function_call_output", "custom_tool_call_output"}:
            call_id = payload.get("call_id")
            if call_id in self.calls:
                call, owner = self.calls.pop(call_id)
                self.touch(owner)
                call.update(result=output_text(payload.get("output", "")), pending=False)
            elif call_id not in self.call_ids:
                step.update(content="工具输出（源日志未包含对应调用）", phase="commentary",
                            tool_calls=[{"name": "tool_output", "args": {},
                                         "result": output_text(payload.get("output", ""))}])
                self.append(step)
            self.touch(self.current)["last_activity_at"] = timestamp
            return
        else:
            return
        self.append(step)


def parse_turns(records, assets=None):
    roles = {record.get("payload", {}).get("role") for record in records
             if record.get("type") == "response_item"}
    parser = Parser(assets, roles=roles)
    parser.feed(records)
    return parser.turns
