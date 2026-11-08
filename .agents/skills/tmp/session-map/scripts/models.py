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

