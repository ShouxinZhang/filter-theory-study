"""Initialize session-local memory documents without inferring or approving entries."""
from pathlib import Path


TEMPLATES = Path(__file__).resolve().parent.parent / "references/templates"
DOCUMENTS = ("agent-memory-drafts.md", "memory.md")


def ensure_memory(session_directory, header):
    """Create only missing files; preserve human edits, including intentionally empty files.

    The caller holds the session sync lock. Exclusive creation also protects edits
    from other callers. Neither transcripts nor legacy memory are used as content:
    deciding what becomes approved memory remains a human review operation.
    """
    directory = session_directory / "memory"
    (directory / "references").mkdir(parents=True, exist_ok=True)
    for name in DOCUMENTS:
        destination = directory / name
        if destination.exists():
            continue
        content = (TEMPLATES / name).read_text(encoding="utf-8")
        try:
            with destination.open("x", encoding="utf-8") as stream:
                stream.write(header.rstrip() + "\n\n" + content)
        except FileExistsError:
            # Another writer, or an existing symlink, always takes precedence.
            pass
