"""Adapt Antigravity transcripts into the shared user/steps turn structure."""

import re

from models import TurnParser

TRUNCATED_OUTPUT = re.compile(
    r"\A((?:Created At: [^\n]+\n)?(?:Completed At: [^\n]+\n)?)"
    r"The tool's output was truncated due to being too long\. "
    r"You can find the full output in a file at "
    r"(file:///[^\s\n]+/\.system_generated/steps/(\d+)/output\.txt)\.\n+"
    r"Here is a preview with the middle of the output truncated:\n",
)


def matches(records):
    return any(record.get("type") == "USER_INPUT" for record in records)


def session_id(records, path):
    return path.parents[2].name


def find_paths(root, prefix):
    return root.glob(f"{prefix}*/.system_generated/logs/transcript_full.jsonl")


class Parser(TurnParser):
    """Keep raw steps per turn; pairing is redone only for turns that changed."""

    def __init__(self, assets=None, **hints):
        super().__init__(assets, **hints)
        self.raw = []

    def feed(self, records):
        changed = set()
        for record in records:
            if record.get("type") == "USER_INPUT":
                self.raw.append({"user": record, "steps": []})
                changed.add(len(self.raw) - 1)
            elif self.raw:
                self.raw[-1]["steps"].append(record)
                changed.add(len(self.raw) - 1)
        for index in sorted(changed):
            turn = {**normalize_turn(self.raw[index]), "index": index}
            if index < len(self.turns):
                self.touch(self.turns[index])
                self.turns[index] = turn
            else:
                self.open_turn(turn)

    def seal(self, index):
        super().seal(index)
        self.raw[index]["steps"] = []


def parse_turns(steps, assets=None):
    parser = Parser(assets)
    parser.feed(steps)
    return parser.turns


def normalize_turn(turn):
    """Pair AGY's adjacent GENERIC outputs and media here, never in the shared renderer."""
    steps = [dict(step) for step in turn["steps"]]
    for index, step in enumerate(steps):
        calls = step.get("tool_calls") or []
        if step.get("type") != "PLANNER_RESPONSE" or not calls:
            continue
        outputs, following = [], index + 1
        while (following < len(steps) and steps[following].get("type") == "GENERIC"
               and len(outputs) < len(calls)):
            outputs.append(steps[following])
            following += 1
        paired = []
        for call_index, call in enumerate(calls):
            generic = outputs[call_index] if call_index < len(outputs) else None
            content = generic.get("content", "") if generic else ""
            entry = {**call, "result": call.get("result", content)}
            media = call.get("media") or (generic.get("media") if generic else None)
            if media:
                entry["media"] = [dict(item) for item in media if isinstance(item, dict)]
            if generic and "output_uri" not in entry:
                match = TRUNCATED_OUTPUT.match(content)
                step_id = generic.get("step_index")
                if match and (step_id is None or str(step_id) == match[3]):
                    entry["output_prefix"] = match[1]
                    entry["output_uri"] = match[2]
            paired.append(entry)
        step["tool_calls"] = paired
    return {**turn, "steps": steps}

