import json
import shutil
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import runtime as sync
import sources
import render as renderer

SID = "11111111-2222-3333-4444-555555555555"
STAMP = "2026-11-04T08:00:00Z"
HEADER = "- agent name: unknown\n- harness: unknown\n- session: unknown\n- time: unknown"


def record(kind, **payload):
    return {"timestamp": STAMP, "type": kind, "payload": payload}


def message(role, text, **extra):
    return record("response_item", type="message", role=role,
                  content=[{"type": "input_text", "text": text}], **extra)


def call(call_id, command):
    return record("response_item", type="function_call", call_id=call_id, name="exec_command",
                  arguments=json.dumps({"cmd": command}))


def output(call_id, text):
    return record("response_item", type="function_call_output", call_id=call_id, output=text)


def claude(kind, content, uuid, **extra):
    stop = extra.pop("stop_reason", None)
    return {"type": kind, "sessionId": SID, "uuid": uuid, "timestamp": STAMP, "isSidechain": False,
            "message": {"role": kind, "content": content, "stop_reason": stop}, **extra}


CODEX = [
    record("session_meta", id=SID),
    record("event_msg", type="task_started", turn_id="t1"),
    message("user", "first question"),
    call("c1", "ls"),
    message("assistant", "first answer"),
    record("event_msg", type="task_started", turn_id="t2"),
    message("user", "second question"),
    output("c1", "LATE LISTING"),
    call("c2", "pwd"),
    output("c2", "WORKDIR"),
    message("assistant", "second answer"),
    message("user", "third question"),
    record("event_msg", type="task_complete", turn_id="t1", duration_ms=9000),
    message("assistant", "third answer"),
]
ANTIGRAVITY = [
    {"type": "USER_INPUT", "created_at": STAMP, "content": "first question"},
    {"type": "PLANNER_RESPONSE", "created_at": STAMP, "tool_calls": [{"name": "one", "args": {}}]},
    {"type": "GENERIC", "created_at": STAMP, "content": "FIRST OUTPUT"},
    {"type": "PLANNER_RESPONSE", "created_at": STAMP, "content": "first answer"},
    {"type": "USER_INPUT", "created_at": STAMP, "content": "second question"},
    {"type": "PLANNER_RESPONSE", "created_at": STAMP, "content": "second answer"},
]
CLAUDE = [
    claude("user", "first question", "u1"),
    claude("assistant", [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}],
           "u2", stop_reason="tool_use"),
    claude("user", "second question", "u3"),
    claude("user", [{"type": "tool_result", "tool_use_id": "t1", "content": "LATE LISTING"}], "u4"),
    claude("assistant", [{"type": "text", "text": "second answer"}], "u5", stop_reason="end_turn"),
    claude("user", "third question", "u6"),
    claude("assistant", [{"type": "text", "text": "third answer"}], "u7", stop_reason="end_turn"),
]


class IncrementalTests(unittest.TestCase):
    def setUp(self):
        # System temp keeps test runs from leaving task folders in the repository.
        self.temporary = tempfile.TemporaryDirectory(prefix="session-map-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "output"
        for target, name, value in ((sync, "SESS", self.output), (sync, "attribution", lambda source: HEADER),
                                    (sources, "CODEX_HOME", self.root / "codex"),
                                    (sources, "BRAIN", self.root / "brain"),
                                    (sources, "CLAUDE_HOME", self.root / "claude")):
            patcher = patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.path = self.root / "log.jsonl"
        self.path.write_bytes(b"")
        self.destination = self.output / SID / "prompts.md"

    def append(self, records, end="\n"):
        with self.path.open("a") as stream:
            stream.write("\n".join(json.dumps(item) for item in records) + end)

    def full(self, harness):
        """What a from-scratch parse of the whole log renders."""
        turns = sources.parse_turns(sync.read_records(self.path), harness)
        return renderer.render(SID, self.path, harness, HEADER, turns)

    def test_every_split_matches_a_full_rebuild(self):
        for harness, records in (("codex", CODEX), ("antigravity", ANTIGRAVITY), ("claude-code", CLAUDE)):
            for step in (1, 2, 3, len(records)):
                with self.subTest(harness=harness, step=step):
                    self.path.write_bytes(b"")
                    shutil.rmtree(self.output, ignore_errors=True)
                    source, cache = sync.Source(SID, harness, self.path), {}
                    for start in range(0, len(records), step):
                        self.append(records[start:start + step])
                        sync.sync_source(source, subscribe=True, cache=cache)
                        self.assertEqual(self.destination.read_text(), self.full(harness))
                    self.assertEqual(self.destination.read_text().count("question"), 2 * len(cache[SID].bodies))

    def test_later_syncs_read_only_appended_bytes(self):
        source, cache, reads = sync.Source(SID, "codex", self.path), {}, []
        original = sources.read_batch

        def spy(stream, path, line_number, **options):
            start = stream.tell()
            result = original(stream, path, line_number, **options)
            reads.append((start, len(result[0])))
            return result

        self.append(CODEX[:5])
        size = self.path.stat().st_size
        with patch.object(sources, "read_batch", spy):
            sync.sync_source(source, subscribe=True, cache=cache)
            self.append(CODEX[5:7])
            sync.sync_source(source, cache=cache)
            sync.sync_source(source, cache=cache)
        self.assertEqual(reads, [(0, 5), (size, 2), (self.path.stat().st_size, 0)])
        with patch.object(sources, "read_batch", spy):
            sync.sync_source(source)
        self.assertEqual(reads[-1], (0, 7))

    def test_finished_turns_release_steps_but_stay_rendered(self):
        source, cache = sync.Source(SID, "claude-code", self.path), {}
        self.append(CLAUDE[:3])
        sync.sync_source(source, subscribe=True, cache=cache)
        turns = cache[SID].parser.turns
        # The first turn still waits for a tool result, so it must stay editable.
        self.assertFalse(turns[0].get("sealed"))
        self.append(CLAUDE[3:])
        sync.sync_source(source, cache=cache)
        self.assertEqual([bool(turn.get("sealed")) for turn in turns], [True, True, False])
        self.assertEqual(turns[0]["steps"], [])
        self.assertFalse(cache[SID].parser.calls)
        text = self.destination.read_text()
        for expected in ("LATE LISTING", "second answer", "third answer"):
            self.assertIn(expected, text)

    def test_update_to_a_released_turn_rebuilds_without_sealing(self):
        source, cache = sync.Source(SID, "codex", self.path), {}
        self.append(CODEX[:12])
        sync.sync_source(source, subscribe=True, cache=cache)
        self.assertTrue(cache[SID].parser.turns[0].get("sealed"))
        self.append(CODEX[12:])
        sync.sync_source(source, cache=cache)
        self.assertEqual(cache[SID].hints, {"seal": False})
        self.assertFalse(any(turn.get("sealed") for turn in cache[SID].parser.turns))
        self.assertEqual(self.destination.read_text(), self.full("codex"))
        self.assertIn("Worked for 9s", self.destination.read_text())

    def test_legacy_events_then_response_items_restart_with_roles(self):
        source, cache = sync.Source(SID, "codex", self.path), {}
        self.append([record("session_meta", id=SID),
                     record("event_msg", type="user_message", message="shown once")])
        sync.sync_source(source, subscribe=True, cache=cache)
        self.assertIn("> shown once", self.destination.read_text())
        self.append([message("user", "shown once"), message("assistant", "answer")])
        sync.sync_source(source, cache=cache)
        text = self.destination.read_text()
        self.assertEqual(text, self.full("codex"))
        self.assertEqual(text.count("> shown once"), 1)
        self.assertEqual(cache[SID].hints["roles"], ["assistant", "user"])

    def test_rewritten_or_truncated_log_rebuilds(self):
        source, cache = sync.Source(SID, "codex", self.path), {}
        self.append(CODEX[:7])
        sync.sync_source(source, subscribe=True, cache=cache)
        self.path.write_bytes(b"")
        self.append([record("session_meta", id=SID), message("user", "replaced")])
        sync.sync_source(source, cache=cache)
        self.assertEqual(self.destination.read_text(), self.full("codex"))
        self.assertNotIn("first question", self.destination.read_text())
        # Same length, different bytes before the offset.
        data = self.path.read_bytes().replace(b"replaced", b"REPLACED")
        self.path.write_bytes(data)
        self.append([message("assistant", "after rewrite")])
        sync.sync_source(source, cache=cache)
        self.assertEqual(self.destination.read_text(), self.full("codex"))
        self.assertIn("> REPLACED", self.destination.read_text())

    def test_unfinished_tail_waits_and_corrupt_line_drops_progress(self):
        source, cache = sync.Source(SID, "codex", self.path), {}
        self.append(CODEX[:3])
        line = json.dumps(message("assistant", "delayed answer"))
        with self.path.open("a") as stream:
            stream.write(line[:20])
        sync.sync_source(source, subscribe=True, cache=cache)
        state = json.loads((self.output / SID / ".sync-state.json").read_text())
        self.assertTrue(state["incomplete_tail"])
        self.assertNotIn("delayed answer", self.destination.read_text())
        with self.path.open("a") as stream:
            stream.write(line[20:] + "\n")
        sync.sync_source(source, cache=cache)
        self.assertIn("delayed answer", self.destination.read_text())
        before = self.destination.read_bytes()
        with self.path.open("a") as stream:
            stream.write("not json\n")
        with self.assertRaisesRegex(ValueError, r"log\.jsonl:5: 无效 JSONL 记录"):
            sync.sync_source(source, cache=cache)
        self.assertEqual(self.destination.read_bytes(), before)
        self.assertNotIn(SID, cache)

    def test_restarted_watcher_skips_logs_synced_completely(self):
        source = sync.Source(SID, "codex", self.path)
        self.append(CODEX[:5])
        sync.sync_source(source, subscribe=True)
        directory = self.output / SID
        self.assertEqual(sync.synced_signature(directory), sync.source_signature(self.path))
        self.append(CODEX[5:7])
        self.assertNotEqual(sync.synced_signature(directory), sync.source_signature(self.path))
        sync.record_sync_error(directory, ValueError("broken"))
        self.assertIsNone(sync.synced_signature(directory))

    def test_identification_reads_only_the_head(self):
        self.append([record("session_meta", id=SID), message("user", "question")])
        with self.path.open("a") as stream:
            stream.write("not json\n" * 3)
        self.assertEqual(sources.source_from_path(self.path).sid, SID)

    def test_antigravity_media_splits_match_full_sync(self):
        user_img = self.root / "user.png"
        tool_img = self.root / "tool.png"
        user_img.write_bytes(b"\x89PNG\r\n\x1a\nuser")
        tool_img.write_bytes(b"\x89PNG\r\n\x1a\ntool")
        records = [
            {"type": "USER_INPUT", "created_at": STAMP, "content": "<USER_REQUEST>see</USER_REQUEST>",
             "media": [{"mime_type": "image/png", "uri": str(user_img)}]},
            {"type": "PLANNER_RESPONSE", "created_at": STAMP,
             "tool_calls": [{"name": "read_file", "args": {"Path": str(tool_img)}}]},
            {"type": "GENERIC", "created_at": STAMP, "content": "Showing binary file",
             "media": [{"mime_type": "image/png", "uri": tool_img.as_uri()}]},
            {"type": "PLANNER_RESPONSE", "created_at": STAMP, "content": "done"},
        ]
        reference_dir = self.root / "reference"
        expected = sync.render(SID, self.path, "antigravity", HEADER, records=records,
                               assets=sync.AssetStore(reference_dir))
        for step in (1, 2, len(records)):
            with self.subTest(step=step):
                self.path.write_bytes(b"")
                shutil.rmtree(self.output, ignore_errors=True)
                source, cache = sync.Source(SID, "antigravity", self.path), {}
                for start in range(0, len(records), step):
                    self.append(records[start:start + step])
                    sync.sync_source(source, subscribe=True, cache=cache)
                self.assertEqual(self.destination.read_text(), expected)
                self.assertEqual(len(list((self.output / SID / "assets/media").iterdir())), 2)


if __name__ == "__main__":
    unittest.main()
