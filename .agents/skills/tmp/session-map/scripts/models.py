"""Shared source identity and timestamps; no I/O or harness dependencies."""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class Source:
    sid: str
    harness: str
    path: Path


def ts(s):
    value = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(TZ)



class Restart(Exception):
    """An incremental parse cannot continue; rebuild from the start with these hints."""

    def __init__(self, **hints):
        super().__init__(f"restart with {hints}")
        self.hints = hints


class TurnParser:
    """Resumable adapter base: feed appended records, read `turns`, drain `dirty`.

    `dirty` holds the indexes of turns whose content changed since it was last
    cleared. A sealed turn has released its steps after rendering; touching it
    again requires a rebuild without sealing.
    """

    def __init__(self, assets=None, **hints):
        self.assets = assets
        self.hints = hints
        self.turns = []
        self.dirty = set()

    def open_turn(self, turn):
        turn["index"] = len(self.turns)
        self.turns.append(turn)
        self.dirty.add(turn["index"])
        return turn

    def touch(self, turn):
        if turn.get("sealed"):
            raise Restart(seal=False)
        self.dirty.add(turn["index"])
        return turn

    def feed(self, records):
        for record in records:
            self.accept(record)

    def accept(self, record):
        raise NotImplementedError

    def seal(self, index):
        self.turns[index].update(steps=[], sealed=True)


def pending(turn):
    return any(call.get("pending") for step in turn["steps"] for call in step.get("tool_calls") or [])
