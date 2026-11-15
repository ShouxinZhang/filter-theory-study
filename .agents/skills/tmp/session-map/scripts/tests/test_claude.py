import base64
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import runtime as sync
import sync as cli
import sources
import claude
import render as renderer
SOURCE_ATTRIBUTION = sync.attribution

SID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
STAMP = "2026-11-14T23:00:00.000Z"
LATER = "2026-11-14T23:00:42.000Z"
HEADER = "- agent name: unknown\n- harness: unknown\n- session: unknown\n- time: unknown"
COUNTER = iter(range(10**6))


def entry(kind, content, stamp=STAMP, sid=SID, **extra):
    message = {"role": kind, "content": content}
    for key in ("model", "stop_reason"):
        if key in extra:
            message[key] = extra.pop(key)
    return {"type": kind, "sessionId": sid, "uuid": f"uuid-{next(COUNTER)}", "timestamp": stamp,
            "isSidechain": False, "message": message, **extra}


def user(text, **extra):
    return entry("user", text, **extra)


def assistant(*blocks, **extra):
    return entry("assistant", list(blocks), **extra)


def use(call_id, name, **arguments):
    return {"type": "tool_use", "id": call_id, "name": name, "input": arguments}


def output(call_id, content):
    return entry("user", [{"type": "tool_result", "tool_use_id": call_id, "content": content}])


class ClaudeTests(unittest.TestCase):
    def setUp(self):
        # System temp keeps test runs from leaving task folders in the repository.
        self.temporary = tempfile.TemporaryDirectory(prefix="session-map-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.claude_home = self.root / "claude"
        self.output = self.root / "output"
        for name, value in (("CODEX_HOME", self.root / "codex"), ("BRAIN", self.root / "brain"),
                            ("CLAUDE_HOME", self.claude_home), ("SESS", self.output)):
            patcher = patch.object(sync if name == "SESS" else sources, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(sync, "attribution", return_value=HEADER)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_claude(self, records, sid=SID, project="-home-user-repo"):
        path = self.claude_home / "projects" / project / f"{sid}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        bookkeeping = [{"type": "custom-title", "customTitle": "title", "sessionId": sid},
                       {"type": "api-request-blob", "sessionId": sid, "hash": "h",
                        "message": {"role": "user", "content": [{"type": "text", "text": "LEAK"}]}}]
        path.write_text("".join(json.dumps(item) + "\n" for item in [*bookkeeping, *records]))
        return path

    def run_management(self, *args):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = cli.manage([*args, "--json"])
        return code, json.loads(stream.getvalue())

    def test_calls_pair_by_id_and_tools_use_renderer_vocabulary(self):
        records = [
            user("<system-reminder>\nhost context\n</system-reminder>\nquestion"),
            assistant({"type": "thinking", "thinking": "", "signature": "SECRET"},
                      {"type": "redacted_thinking", "data": "SECRET"}, stop_reason="tool_use"),
            assistant({"type": "text", "text": "looking"}, stop_reason="tool_use"),
            assistant(use("t1", "Bash", command="ls", description="List files"),
                      use("t2", "Edit", file_path="/r/a.md", old_string="x", new_string="y"),
                      stop_reason="tool_use"),
            output("t2", [{"type": "text", "text": "EDITED"}]),
            output("t1", "LISTING"),
            assistant({"type": "thinking", "thinking": "visible thought"}),
            assistant({"type": "text", "text": "answer"}, stamp=LATER, stop_reason="end_turn"),
        ]
        before = json.dumps(records)
        turns = claude.parse_turns(records)
        self.assertEqual(json.dumps(records), before)
        self.assertEqual(len(turns), 1)
        turn = turns[0]
        self.assertEqual(turn["user"]["content"], "question")
        self.assertEqual((turn["status"], turn["ended_at"]), ("completed", LATER))
        calls = [call for step in turn["steps"] for call in step.get("tool_calls") or []]
        self.assertEqual([(call["name"], call["result"], call["pending"]) for call in calls],
                         [("run_command", "LISTING", False), ("edit_file", "EDITED", False)])
        self.assertEqual(calls[0]["args"], {"CommandLine": "ls", "toolSummary": "List files"})
        text = renderer.render(SID, Path("not-a-real-log"), "claude-code", HEADER, turns)
        self.assertIn("> question", text)
        self.assertIn("Ran List files", text)
        self.assertIn("visible thought", text)
        self.assertIn("Worked for 42s · 2 tools", text)
        self.assertTrue(text.rstrip().endswith("answer\n\n---"))
        for hidden in ("SECRET", "host context", "LEAK"):
            self.assertNotIn(hidden, text)

    def test_non_prompts_interruption_and_replayed_records(self):
        first = user("first")
        records = [
            first, first,
            entry("user", "meta caveat", isMeta=True),
            entry("user", "subagent prompt", isSidechain=True),
            assistant(use("t1", "Read", file_path="/r/a.md", limit=5), stop_reason="tool_use"),
            entry("user", [{"type": "text", "text": "[Request interrupted by user for tool use]"}]),
            user("second"),
            user("summary of earlier turns", isCompactSummary=True),
            user("background task finished", origin={"kind": "task-notification"}),
            assistant({"type": "text", "text": "still going"}),
        ]
        turns = claude.parse_turns(records)
        self.assertEqual([turn["user"]["content"] for turn in turns], ["first", "second"])
        self.assertEqual(turns[0]["status"], "interrupted")
        call = turns[0]["steps"][0]["tool_calls"][0]
        self.assertEqual((call["name"], call["args"], call["pending"]),
                         ("read_file", {"Path": "/r/a.md", "limit": 5}, True))
        self.assertEqual(turns[1]["status"], "working")
        notes = [step["content"] for step in turns[1]["steps"]]
        self.assertIn("压缩", notes[0])
        self.assertEqual(notes[1:], ["background task finished", "still going"])

    def test_images_in_prompts_and_tool_results_are_externalized(self):
        binary = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 20
        image = {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                             "data": base64.b64encode(binary).decode()}}
        path = self.write_claude([
            entry("user", [{"type": "text", "text": "see"}, image]),
            assistant(use("t1", "Screenshot"), stop_reason="tool_use"),
            output("t1", [image]),
            assistant({"type": "text", "text": "done"}, stop_reason="end_turn"),
        ])
        sync.sync(None, "auto", path)
        text = (self.output / SID / "prompts.md").read_text()
        self.assertNotIn("base64", text)
        media = list((self.output / SID / "assets/media").iterdir())
        self.assertEqual([item.read_bytes() for item in media], [binary])
        self.assertIn(f"![图像附件](assets/media/{media[0].name})", text)

    def test_resolve_by_prefix_current_session_and_harness_validation(self):
        path = self.write_claude([user("question"),
                                  assistant({"type": "text", "text": "answer"}, stop_reason="end_turn")])
        subagent = path.parent / SID / "subagents" / f"agent-{SID}.jsonl"
        subagent.parent.mkdir(parents=True)
        subagent.write_text(path.read_text())
        source = sync.resolve_source(SID[:8])
        self.assertEqual((source.sid, source.harness, source.path), (SID, "claude-code", path))
        with self.assertRaisesRegex(ValueError, "与 --harness codex 不符"):
            sync.resolve_source(None, "codex", path)
        with patch.dict(os.environ, {"CLAUDE_CODE_SESSION_ID": SID}, clear=True):
            code, result = self.run_management("subscribe", "--current")
        self.assertEqual(code, 0)
        self.assertEqual((result["subscription"]["id"], result["subscription"]["harness"]),
                         (SID, "claude-code"))
        self.assertIn("\n\nanswer\n", (self.output / SID / "prompts.md").read_text())
        code, result = self.run_management("list", "--harness", "claude-code")
        self.assertEqual([item["id"] for item in result["subscriptions"]], [SID])

    def test_resumed_log_keeps_the_file_session_id(self):
        path = self.write_claude([user("old", sid="00000000-1111-2222-3333-444444444444"),
                                  user("new")])
        self.assertEqual(sync.resolve_source(None, "auto", path).sid, SID)

    def test_attribution_uses_source_config_directory(self):
        path = self.write_claude([user("question"),
                                  assistant({"type": "text", "text": "a"}, model="claude-test-9")])
        with patch.dict(os.environ, {"AI_MODEL_NAME": "wrong-model", "CLAUDE_CODE_SESSION_ID": "other"}):
            header = SOURCE_ATTRIBUTION(sync.Source(SID, "claude-code", path))
        self.assertIn("agent name: claude-test-9", header)
        self.assertIn("harness: claude-code", header)
        self.assertIn(f"session: {SID[:8]}", header)


if __name__ == "__main__":
    unittest.main()
