"""Regression tests for review boundaries and non-destructive memory initialization."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import runtime

SID = "11111111-2222-3333-4444-555555555555"
HEADER = "- agent name: source-model\n- harness: codex\n- session: 11111111\n- time: source-time"


class MemoryTests(unittest.TestCase):
    def setUp(self):
        root = runtime.REPO / ".agents/.tmp/task" / runtime.datetime.now(runtime.TZ).strftime("%Y-%m")
        root /= runtime.datetime.now(runtime.TZ).strftime("%Y-%m-%d") + "_session-memory/outputs/test-data"
        root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "sessions"
        for name, value in (("SESS", self.output), ("attribution", lambda source: HEADER)):
            patcher = patch.object(runtime, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def source(self, sid=SID):
        path = self.root / f"{sid}.jsonl"
        records = [
            {"type": "session_meta", "payload": {"id": sid}},
            {"type": "response_item", "timestamp": "2026-11-12T00:00:00Z", "payload": {
                "type": "message", "role": "user", "content": [
                    {"type": "input_text", "text": "TRANSCRIPT_IS_NOT_APPROVED_MEMORY"}]}},
        ]
        path.write_text("".join(json.dumps(row) + "\n" for row in records))
        return runtime.Source(sid, "codex", path)

    def test_initialize_bound_header_without_promoting_transcript_or_legacy(self):
        source = self.source()
        folder = self.output / SID
        folder.mkdir(parents=True)
        legacy = folder / "memory.md"
        legacy.write_text("LEGACY_REQUIRES_REVIEW")
        runtime.sync_source(source, subscribe=True)
        for name in ("memory.md", "agent-memory-drafts.md"):
            text = (folder / "memory" / name).read_text()
            self.assertTrue(text.startswith(HEADER))
            self.assertNotIn("TRANSCRIPT_IS_NOT_APPROVED_MEMORY", text)
            self.assertNotIn("LEGACY_REQUIRES_REVIEW", text)
        self.assertEqual(legacy.read_text(), "LEGACY_REQUIRES_REVIEW")
        self.assertTrue((folder / "memory/references").is_dir())
        info = runtime.subscription_info(folder)
        self.assertEqual(info["memory_path"], str(folder / "memory/memory.md"))
        self.assertEqual(info["memory_drafts_path"], str(folder / "memory/agent-memory-drafts.md"))
        self.assertEqual(info["memory_references_path"], str(folder / "memory/references"))

    def test_resync_preserves_human_content_empty_file_and_media_mtimes(self):
        source = self.source()
        runtime.sync_source(source, subscribe=True)
        folder = self.output / SID
        preserved = {
            folder / "memory/memory.md": b"",  # An intentional human deletion of all entries.
            folder / "memory/agent-memory-drafts.md": "- 人类修改后的候选\n  第二行\n".encode(),
            folder / "memory/references/picture.png": b"\x89PNG\r\nunchanged",
            folder / "map.md": b"human topic map",
        }
        for path, data in preserved.items():
            path.write_bytes(data)
        stamps = {path: path.stat().st_mtime_ns for path in preserved}
        with source.path.open("a") as stream:
            stream.write(json.dumps({"type": "event_msg", "payload": {
                "type": "token_count", "usage": 100}}) + "\n")
        with patch.object(runtime, "attribution", return_value=HEADER.replace("source-time", "later")):
            runtime.sync_source(source)
        for path, data in preserved.items():
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual(path.stat().st_mtime_ns, stamps[path])

    def test_missing_draft_is_initialized_without_touching_approved_memory(self):
        source = self.source()
        runtime.sync_source(source, subscribe=True)
        directory = self.output / SID / "memory"
        approved = directory / "memory.md"
        approved.write_text("- 已审核且保留的记忆\n")
        (directory / "agent-memory-drafts.md").unlink()
        runtime.sync_source(source)
        self.assertEqual(approved.read_text(), "- 已审核且保留的记忆\n")
        self.assertTrue((directory / "agent-memory-drafts.md").read_text().startswith(HEADER))

    def test_sessions_do_not_share_approved_entries(self):
        first = self.source()
        second = self.source(SID[:-1] + "6")
        runtime.sync_source(first, subscribe=True)
        approved = self.output / first.sid / "memory/memory.md"
        approved.write_text("- SESSION_ONE_ONLY\n")
        runtime.sync_source(second, subscribe=True)
        runtime.sync_source(first)
        self.assertNotIn("SESSION_ONE_ONLY", (self.output / second.sid / "memory/memory.md").read_text())
        self.assertEqual(approved.read_text(), "- SESSION_ONE_ONLY\n")
        self.assertFalse((self.output / "memory").exists())


if __name__ == "__main__":
    unittest.main()
