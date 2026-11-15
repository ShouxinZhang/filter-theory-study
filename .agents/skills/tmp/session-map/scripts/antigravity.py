"""Adapt Antigravity transcripts into the shared user/steps turn structure."""

from models import TurnParser


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

