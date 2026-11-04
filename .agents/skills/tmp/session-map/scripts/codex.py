"""Adapt local Codex rollout records to session-map's renderable turns."""

import json
import re


def text_content(content):
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if block.get("type") in {"input_text", "output_text", "text", "summary_text"}:
            parts.append(block.get("text", ""))
        elif block.get("type") in {"input_image", "image"}:
            parts.append("[图像附件]")
    return "\n\n".join(parts)


def prompt_text(content):
    """Exclude host-injected context while retaining actual user text."""
    parts = []
    for block in content or []:
        text = text_content([block]).strip()
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
    return "\n\n".join(parts)


def output_text(value):
    if isinstance(value, list) and all(isinstance(block, dict) and block.get("type") in
                                      {"input_text", "output_text", "text"} for block in value):
        return text_content(value)
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)


def parse_turns(records):
    # Rollouts can contain UI events and Responses items for the same message.
    # Responses items are canonical when available, including on Desktop.
    response_roles = {
        record.get("payload", {}).get("role")
        for record in records
        if record.get("type") == "response_item"
    }
    result, calls, seen_items = [], {}, set()
    current, active_turn_id = None, None
    by_turn_id = {}

    def start_prompt(text, timestamp):
        nonlocal current
        current = {
            "user": {"content": text, "created_at": timestamp},
            "steps": [],
            "status": "working",
        }
        result.append(current)
        if active_turn_id:
            by_turn_id[active_turn_id] = current

    for record in records:
        payload = record.get("payload") or {}
        kind = payload.get("type")
        timestamp = record.get("timestamp", "")
        if record.get("type") == "event_msg":
            if kind == "task_started":
                active_turn_id = payload.get("turn_id")
            elif kind == "user_message" and "user" not in response_roles:
                start_prompt(payload.get("message", ""), timestamp)
            elif kind == "agent_message" and "assistant" not in response_roles and current:
                current["steps"].append({
                    "type": "PLANNER_RESPONSE", "created_at": timestamp,
                    "content": payload.get("message", ""), "phase": "final",
                })
            elif kind in {"task_complete", "turn_aborted"}:
                target = by_turn_id.get(payload.get("turn_id"), current)
                if target is not None:
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
            continue

        if record.get("type") == "compacted" and current:
            current["steps"].append({
                "type": "PLANNER_RESPONSE", "created_at": timestamp,
                "content": "[上下文已压缩，原始记录以本地日志保留范围为准]",
                "phase": "commentary",
            })
        if record.get("type") != "response_item":
            continue
        item_id = payload.get("id")
        if item_id:
            if item_id in seen_items:
                continue
            seen_items.add(item_id)
        if kind == "message" and payload.get("role") == "user":
            text = prompt_text(payload.get("content"))
            if text:
                start_prompt(text, timestamp)
            continue
        if current is None:
            continue
        step = {"type": "PLANNER_RESPONSE", "created_at": timestamp}
        if kind == "message" and payload.get("role") == "assistant":
            phase = payload.get("phase") or payload.get("channel")
            if phase in {"analysis", "justify", "confidence"}:
                continue
            step.update(content=text_content(payload.get("content")), phase=phase or "final")
        elif kind == "reasoning":
            summary = text_content(payload.get("summary"))
            if not summary:
                continue
            step.update(thinking=summary, thought_label="Reasoning summary", phase="commentary")
        elif kind in {"function_call", "custom_tool_call"}:
            call_id = payload.get("call_id") or item_id
            if call_id in calls:
                continue
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
                calls[call_id] = call
            step.update(tool_calls=[call], phase="commentary")
        elif kind in {"function_call_output", "custom_tool_call_output"}:
            call = calls.get(payload.get("call_id"))
            if call is not None:
                call.update(result=output_text(payload.get("output", "")), pending=False)
            else:
                step.update(content="工具输出（源日志未包含对应调用）", phase="commentary",
                            tool_calls=[{"name": "tool_output", "args": {},
                                         "result": output_text(payload.get("output", ""))}])
                current["steps"].append(step)
            current["last_activity_at"] = timestamp
            continue
        else:
            continue
        current["steps"].append(step)
    return result
