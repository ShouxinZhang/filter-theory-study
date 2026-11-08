"""Adapt Antigravity transcripts into the shared user/steps turn structure."""


def matches(records):
    return any(record.get("type") == "USER_INPUT" for record in records)


def session_id(records, path):
    return path.parents[2].name


def find_paths(root, prefix):
    return root.glob(f"{prefix}*/.system_generated/logs/transcript_full.jsonl")


def parse_turns(steps, assets=None):
    cur = None
    for d in steps:
        if d.get("type") == "USER_INPUT":
            if cur:
                yield normalize_turn(cur)
            cur = {"user": d, "steps": []}
        elif cur:
            cur["steps"].append(d)
    if cur:
        yield normalize_turn(cur)


def normalize_turn(turn):
    """Pair AGY's adjacent GENERIC outputs here, never in the shared renderer."""
    steps = [dict(step) for step in turn["steps"]]
    for index, step in enumerate(steps):
        calls = step.get("tool_calls") or []
        if step.get("type") != "PLANNER_RESPONSE" or not calls:
            continue
        results, following = [], index + 1
        while (following < len(steps) and steps[following].get("type") == "GENERIC"
               and len(results) < len(calls)):
            results.append(steps[following].get("content", ""))
            following += 1
        results.extend([""] * (len(calls) - len(results)))
        step["tool_calls"] = [{**call, "result": call.get("result", result)}
                              for call, result in zip(calls, results)]
    return {**turn, "steps": steps}

