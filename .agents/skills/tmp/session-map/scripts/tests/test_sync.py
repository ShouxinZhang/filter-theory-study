import base64
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.parse import quote, unquote, urlsplit
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import runtime as sync
import sync as cli
import sources
import codex
import antigravity
import render as renderer
SOURCE_ATTRIBUTION = sync.attribution

SID = "11111111-2222-3333-4444-555555555555"
STAMP = "2026-11-04T08:00:00Z"
HEADER = "- agent name: unknown\n- harness: unknown\n- session: unknown\n- time: unknown"


def record(kind, **payload):
    return {"timestamp": STAMP, "type": kind, "payload": payload}


def message(role, text, **extra):
    return record("response_item", type="message", role=role,
                  content=[{"type": "input_text", "text": text}], **extra)


class SyncTests(unittest.TestCase):
    def setUp(self):
        task = sync.REPO / ".agents/.tmp/task" / sync.datetime.now(sync.TZ).strftime("%Y-%m")
        task /= sync.datetime.now(sync.TZ).strftime("%Y-%m-%d") + "_session-map-codex"
        for name in ("plans", "logs", "reports"):
            (task / "docs" / name).mkdir(parents=True, exist_ok=True)
        temporary_root = task / "outputs/test-data"
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_root)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.codex_home = self.root / "codex"
        self.brain = self.root / "brain"
        self.output = self.root / "output"
        for name, value in (("CODEX_HOME", self.codex_home), ("BRAIN", self.brain), ("SESS", self.output)):
            patcher = patch.object(sync if name == "SESS" else sources, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(sync, "attribution", return_value=HEADER)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_codex(self, records, sid=SID):
        path = self.codex_home / "sessions/2026/11/04" / f"rollout-date-{sid}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        content = [record("session_meta", id=sid), *records]
        path.write_text("".join(json.dumps(item) + "\n" for item in content))
        return path

    def test_media_externalized_deduplicated_and_clickable(self):
        binary = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 200
        encoded = base64.b64encode(binary).decode()
        uri = "data:image/png;base64," + encoded
        path = self.write_codex([
            record("response_item", type="message", role="user", content=[
                {"type": "input_text", "text": "image question"},
                {"type": "input_image", "image_url": uri}]),
            record("response_item", type="function_call", name="images", call_id="img",
                   arguments=json.dumps({"reference": uri})),
            record("response_item", type="function_call_output", call_id="img", output=[
                {"type": "image", "mimeType": "image/png", "data": encoded},
                {"type": "input_image", "image_url": uri}]),
            message("assistant", "completed"),
        ])
        sync.sync_source(sync.Source(SID, "codex", path), subscribe=True)
        folder = self.output / SID
        media = list((folder / "assets/media").iterdir())
        self.assertEqual(len(media), 1)
        self.assertEqual(media[0].read_bytes(), binary)
        content = (folder / "prompts.md").read_text()
        self.assertNotIn(encoded, content)
        self.assertIn(f"](assets/media/{media[0].name})", content)
        self.assertIn('id="p1"', content)
        before = media[0].stat().st_mtime_ns
        sync.sync_source(sync.Source(SID, "codex", path))
        self.assertEqual(media[0].stat().st_mtime_ns, before)

    def test_large_tools_saved_in_full_with_bounded_preview(self):
        output = "BEGIN\n" + "long line " * 10000 + "\nEND"
        path = self.write_codex([
            message("user", "read tool output"),
            record("response_item", type="function_call", name="read", call_id="r", arguments="{}"),
            record("response_item", type="function_call_output", call_id="r", output=output),
            message("assistant", "final answer retained"),
        ])
        sync.sync_source(sync.Source(SID, "codex", path), subscribe=True)
        folder = self.output / SID
        content = (folder / "prompts.md").read_text()
        self.assertLess(len(content), 5000)
        self.assertIn("final answer retained", content)
        self.assertIn("完整工具记录", content)
        full = list((folder / "assets/tool-output").iterdir())
        self.assertEqual(len(full), 1)
        self.assertIn(output, full[0].read_text())

    def test_noop_or_ignored_event_keeps_document_mtime(self):
        path = self.write_codex([message("user", "unchanged")])
        source = sync.Source(SID, "codex", path)
        sync.sync_source(source, subscribe=True)
        destination = self.output / SID / "prompts.md"
        before = destination.stat().st_mtime_ns
        with path.open("a") as stream:
            stream.write(json.dumps(record("event_msg", type="token_count", usage=100)) + "\n")
        with patch.object(sync, "attribution", return_value=HEADER.replace("time: unknown", "time: later")):
            sync.sync_source(source)
        self.assertEqual(before, destination.stat().st_mtime_ns)
        with path.open("a") as stream:
            stream.write(json.dumps(message("assistant", "new visible answer")) + "\n")
        sync.sync_source(source)
        self.assertIn("new visible answer", destination.read_text())
        self.assertNotEqual(before, destination.stat().st_mtime_ns)

    def test_invalid_base64_preserved_without_external_reads(self):
        store = sync.AssetStore(self.root)
        text = "data:image/png;base64,SECRET_IMAGE https://example.com/picture.png"
        cleaned, refs = store.extract(text)
        self.assertEqual(cleaned, text)
        self.assertFalse(refs)
        self.assertFalse((self.root / "assets").exists())

    def test_attachment_envelope_and_user_image_display(self):
        uri = "data:image/png;base64," + base64.b64encode(b"image-bytes").decode()
        path = self.write_codex([record("response_item", type="message", role="user", content=[
            {"type": "input_text", "text": '# Files mentioned by the user:\n\n## picture.png: /tmp/picture.png\nImage attachment: true\n\n## My request:\n为什么？\n<image name=[Image #1] path="/tmp/picture.png">'},
            {"type": "input_image", "image_url": uri},
            {"type": "input_text", "text": "</image>"}])])
        sync.sync_source(sync.Source(SID, "codex", path), subscribe=True)
        text = (self.output / SID / "prompts.md").read_text()
        self.assertIn("> 为什么？", text)
        self.assertIn("> ![图像附件](assets/media/", text)
        self.assertNotIn("&lt;image", text)
        self.assertNotIn("&lt;/image", text)
        self.assertNotIn("Files mentioned", text)

    def test_assistant_local_images_archived_but_code_unchanged(self):
        picture = self.root / "photo (one).png"
        picture.write_bytes(b"local-image")
        source = (f"![preview](<{picture}>)\n\n"
                  f"`![example](<{picture}>)`\n\n"
                  f"```md\n![example](<{picture}>)\n```\n"
                  "![remote](https://example.com/photo.png)\n")
        path = self.write_codex([message("user", "show image"), message("assistant", source)])
        sync.sync_source(sync.Source(SID, "codex", path), subscribe=True)
        folder = self.output / SID
        text = (folder / "prompts.md").read_text()
        self.assertIn("![preview](assets/media/", text)
        self.assertIn(f"`![example](<{picture}>)`", text)
        self.assertIn(f"```md\n![example](<{picture}>)\n```", text)
        self.assertIn("![remote](https://example.com/photo.png)", text)
        self.assertEqual(list((folder / "assets/media").iterdir())[0].read_bytes(), b"local-image")

    def test_file_hyperlinks_relative_encoded_and_idempotent(self):
        folder = self.root / "archive/session"
        target = self.root / "中文目录" / "note (one) #2.md"
        store = sync.AssetStore(folder)
        url = target.as_uri() + "#L71-L75"
        source = f'[文档](<{url}> "说明")'
        relative = quote(os.path.relpath(target, folder), safe="/.-_~")
        expected = f'[文档]({relative}#L71-L75 "说明")'
        self.assertEqual(store.display_links(source), expected)
        self.assertEqual(store.display_links(expected), expected)
        self.assertEqual((folder / unquote(urlsplit(relative).path)).resolve(), target)
        # Also support raw Unicode and spaces commonly emitted by Antigravity.
        raw = f"[文档](file://{target.parent}/note (one).md)"
        self.assertNotIn("file:", store.display_links(raw))
        self.assertIn("note%20%28one%29.md", store.display_links(raw))

    def test_antigravity_adapter_pairs_outputs_without_mutating_records(self):
        records = [
            {"type": "USER_INPUT", "created_at": STAMP, "content": "question"},
            {"type": "PLANNER_RESPONSE", "created_at": STAMP, "tool_calls": [
                {"name": "one", "args": {}}, {"name": "two", "args": {}}]},
            {"type": "GENERIC", "created_at": STAMP, "content": "FIRST"},
            {"type": "GENERIC", "created_at": STAMP, "content": "SECOND"},
        ]
        before = json.dumps(records)
        turns = list(antigravity.parse_turns(records))
        calls = turns[0]["steps"][0]["tool_calls"]
        self.assertEqual([call["result"] for call in calls], ["FIRST", "SECOND"])
        self.assertEqual(json.dumps(records), before)

    def test_adapters_share_a_renderer_without_source_reads(self):
        inputs = {
            "antigravity": [
                {"type": "USER_INPUT", "created_at": STAMP, "content": "question"},
                {"type": "PLANNER_RESPONSE", "created_at": STAMP, "content": "answer"}],
            "codex": [message("user", "question"), message("assistant", "answer")],
        }
        for harness, records in inputs.items():
            with self.subTest(harness=harness):
                turns = sources.parse_turns(records, harness)
                with patch("builtins.open", side_effect=AssertionError("renderer read a source")):
                    text = renderer.render(SID, Path("not-a-real-log"), harness, HEADER, turns)
                self.assertIn("> question", text)
                self.assertIn("\n\nanswer\n", text)

    def test_service_keeps_the_public_cli_entrypoint(self):
        unit = self.root / "systemd/session-map-sync.service"
        with patch.object(sync, "SERVICE_PATH", unit), patch.object(sync.subprocess, "run"):
            sync.install_service()
        self.assertIn(f"ExecStart=/usr/bin/python3 {SCRIPTS / 'sync.py'} --watch", unit.read_text())
        self.assertNotIn("runtime.py --watch", unit.read_text())

    def test_file_hyperlinks_leave_examples_and_remote_urls_unchanged(self):
        store = sync.AssetStore(self.root)
        link = "[doc](file:///tmp/doc.md)"
        examples = (f"`{link}`\n\n```md\n{link}\n```\n"
                    f"~~~md\n{link}\n~~~\n"
                    "[remote](https://example.com/doc.md)\n"
                    "[share](file://server/share/doc.md)\n"
                    "[relative](../doc.md#section)\n"
                    "![image](file:///tmp/pic.png)\n")
        self.assertEqual(store.display_links(examples), examples)

    def test_antigravity_user_and_final_file_links_rendered(self):
        folder = self.output / SID
        target = self.root / "document.md"
        source = self.brain / SID / ".system_generated/logs/transcript_full.jsonl"
        source.parent.mkdir(parents=True)
        link = f"[document]({target.as_uri()}#L71-L75)"
        records = [
            {"type": "USER_INPUT", "created_at": STAMP, "content": link},
            {"type": "PLANNER_RESPONSE", "created_at": STAMP, "content": link},
        ]
        original = "".join(json.dumps(r) + "\n" for r in records)
        source.write_text(original)
        folder.mkdir(parents=True)
        (folder / "map.md").write_text("user maintained map")
        sync.sync_source(sync.Source(SID, "antigravity", source), subscribe=True)
        body = (folder / "prompts.md").read_text()
        expected = "[document](" + quote(os.path.relpath(target, folder), safe="/.-_~") + "#L71-L75)"
        self.assertIn("> " + expected, body)
        self.assertIn("\n\n" + expected, body)
        self.assertEqual(source.read_text(), original)
        self.assertEqual((folder / "map.md").read_text(), "user maintained map")

    def test_calls_pair_by_id_and_exclude_private_reasoning(self):
        path = self.write_codex([
            message("user", "question"),
            record("event_msg", type="user_message", message="question"),
            record("response_item", type="reasoning", summary=[{"type": "summary_text", "text": "public summary"}],
                   encrypted_content="SECRET_ENCRYPTED", content=[{"text": "SECRET_RAW"}]),
            message("assistant", "SECRET_ANALYSIS", channel="analysis"),
            record("event_msg", type="item_completed", item={"type": "Reasoning", "raw_content": ["SECRET_UI"]}),
            record("response_item", type="function_call", name="first", call_id="a", arguments='{"a":1}'),
            record("response_item", type="custom_tool_call", name="second", call_id="b", input="run second"),
            record("response_item", type="custom_tool_call_output", call_id="b", output="SECOND_OUTPUT"),
            record("response_item", type="function_call_output", call_id="a", output="FIRST_OUTPUT"),
            message("assistant", "DONE", phase="final_answer"),
            record("event_msg", type="task_complete", last_agent_message="DONE", duration_ms=1200),
        ])
        turns = codex.parse_turns(sync.read_records(path))
        self.assertEqual(len(turns), 1)
        calls = [s["tool_calls"][0] for s in turns[0]["steps"] if s.get("tool_calls")]
        self.assertEqual([c["result"] for c in calls], ["FIRST_OUTPUT", "SECOND_OUTPUT"])
        output = sync.render(SID, path, "codex", HEADER)
        self.assertNotIn("SECRET_", output)
        self.assertIn("public summary", output)
        self.assertEqual(output.count("DONE"), 1)
        self.assertIn("Worked for 1s", output)

    def test_context_filter_and_repeated_real_questions(self):
        path = self.write_codex([
            message("user", "<environment_context>config</environment_context>"),
            message("user", "# AGENTS.md instructions for /repo\nrules"),
            message("user", "<external_codex_apps_open_page>{}</external_codex_apps_open_page>"),
            message("user", "same question"),
            message("assistant", "reply", phase="final_answer"),
            message("user", "same question"),
            message("assistant", "progress", phase="commentary"),
        ])
        turns = codex.parse_turns(sync.read_records(path))
        self.assertEqual(len(turns), 2)
        self.assertEqual(turns[1]["user"]["content"], "same question")
        rendered = sync.render(SID, path, "codex", HEADER)
        self.assertIn('id="p2"', rendered)
        self.assertIn("Working for", rendered)

    def test_legacy_events_and_interruption(self):
        path = self.write_codex([
            record("event_msg", type="task_started", turn_id="turn"),
            record("event_msg", type="user_message", message="legacy question"),
            record("event_msg", type="agent_message", message="legacy answer"),
            record("event_msg", type="turn_aborted", turn_id="turn"),
        ])
        rendered = sync.render(SID, path, "codex", HEADER)
        self.assertIn("legacy answer", rendered)
        self.assertIn("Interrupted for", rendered)

    def test_partial_tail_and_corrupt_middle(self):
        path = self.write_codex([message("user", "ready")])
        with path.open("ab") as stream:
            stream.write(b'{"partial": "\xe4\xb8')
        self.assertEqual(len(sync.read_records(path)), 2)
        with path.open("ab") as stream:
            stream.write(b'\n{}\n')
        with self.assertRaises(ValueError):
            sync.read_records(path)

    def test_resolve_sync_map_preserved_and_archive_move(self):
        path = self.write_codex([message("user", "question")])
        self.assertEqual(sync.resolve_source(SID[:8]).path, path)
        sync.sync(SID[:8])
        draft = self.output / SID / "map.md"
        draft.write_text("human draft")
        archived = self.codex_home / "archived_sessions" / path.name
        archived.parent.mkdir(parents=True)
        path.rename(archived)
        sync.sync_all()
        self.assertEqual(draft.read_text(), "human draft")
        binding = json.loads((draft.parent / ".source.json").read_text())
        self.assertEqual(binding["path"], str(archived))

    def test_ambiguous_prefix_and_harness_validation(self):
        path = self.write_codex([message("user", "one")])
        self.write_codex([message("user", "two")], sid=SID[:-1] + "6")
        with self.assertRaises(ValueError):
            sync.resolve_source(SID[:8])
        self.assertEqual(sync.resolve_source(None, source_path=path).sid, SID)
        with self.assertRaises(ValueError):
            sync.resolve_source(SID, "antigravity", path)
        with self.assertRaises(ValueError):
            sync.resolve_source("../escape")

    def test_failed_sync_preserves_last_output(self):
        path = self.write_codex([message("user", "good prompt")])
        sync.sync(SID)
        destination = self.output / SID / "prompts.md"
        before = destination.read_bytes()
        with path.open("a") as stream:
            stream.write("not json\n")
        with self.assertRaises(ValueError):
            sync.sync_source(sync.Source(SID, "codex", path))
        self.assertEqual(destination.read_bytes(), before)

    def test_duplicate_items_and_image_only_prompt(self):
        prompt = record("response_item", type="message", id="image-message", role="user",
                        content=[{"type": "input_image", "image_url": "data:image/png;base64,SECRET_IMAGE"}])
        path = self.write_codex([prompt, prompt])
        turns = codex.parse_turns(sync.read_records(path))
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0]["user"]["content"], "[图像附件]")
        self.assertNotIn("SECRET_IMAGE", sync.render(SID, path, "codex", HEADER))

    def test_antigravity_existing_subscription(self):
        path = self.brain / SID / ".system_generated/logs/transcript_full.jsonl"
        path.parent.mkdir(parents=True)
        records = [
            {"type": "USER_INPUT", "created_at": STAMP, "content": "<USER_REQUEST>old question</USER_REQUEST>"},
            {"type": "PLANNER_RESPONSE", "created_at": STAMP,
             "tool_calls": [{"name": "run_command", "args": {"CommandLine": "echo hi"}}]},
            {"type": "GENERIC", "created_at": STAMP, "content": "hi"},
            {"type": "PLANNER_RESPONSE", "created_at": STAMP, "content": "old answer"},
        ]
        path.write_text("".join(json.dumps(item) + "\n" for item in records))
        folder = self.output / SID
        folder.mkdir(parents=True)
        (folder / "map.md").write_text("legacy map")
        self.assertTrue(sync.sync_all())
        self.assertEqual((folder / "map.md").read_text(), "legacy map")
        self.assertIn("old answer", (folder / "prompts.md").read_text())

    def test_watch_cli_appends_and_keeps_map(self):
        path = self.write_codex([record("turn_context", model="watcher-model"), message("user", "initial")])
        sync.sync(SID)
        draft = self.output / SID / "map.md"
        draft.write_text("keep me")
        env = {**os.environ, "CODEX_HOME": str(self.codex_home), "PYTHONDONTWRITEBYTECODE": "1"}
        command = [sys.executable, str(SCRIPTS / "sync.py"), "--watch", "--interval", "0.05",
                   "--output-root", str(self.output)]
        process = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            with path.open("a") as stream:
                stream.write(json.dumps(message("user", "APPENDED_PROMPT")) + "\n")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if "APPENDED_PROMPT" in (draft.parent / "prompts.md").read_text():
                    break
                time.sleep(0.05)
            else:
                self.fail("watcher did not synchronize appended prompt")
            self.assertEqual(draft.read_text(), "keep me")
            header = (draft.parent / "prompts.md").read_text().split("\n\n", 1)[0]
            self.assertIn("agent name: watcher-model", header)
            self.assertIn("harness: codex", header)
            self.assertIn(f"session: {SID[:8]}", header)
            self.assertEqual(sync.watcher_status()["status"], "running")
            sync.unsubscribe(SID)
            before = (draft.parent / "prompts.md").read_bytes()
            with path.open("a") as stream:
                stream.write(json.dumps(message("user", "AFTER_UNSUBSCRIBE")) + "\n")
            time.sleep(0.2)
            self.assertEqual((draft.parent / "prompts.md").read_bytes(), before)
            self.assertFalse(sync.subscription_info(draft.parent)["watching"])
            sync.sync(SID)
            self.assertIn("AFTER_UNSUBSCRIBE", (draft.parent / "prompts.md").read_text())
        finally:
            process.terminate()
            process.communicate(timeout=5)

    def run_management(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli.manage([*args, "--json"])
        return code, json.loads(output.getvalue())

    def test_management_json_and_read_only_inventory(self):
        code, result = self.run_management("list")
        self.assertEqual(code, 0)
        self.assertEqual(result["subscriptions"], [])
        self.assertFalse(self.output.exists())
        self.write_codex([message("user", "Display title")])
        code, result = self.run_management("subscribe", SID)
        self.assertEqual(code, 0)
        self.assertEqual(result["subscription"]["sync_status"], "up_to_date")
        self.assertEqual(result["subscription"]["name"], "Display title")
        before = {p: p.stat().st_mtime_ns for p in self.output.rglob("*") if p.is_file()}
        with patch.object(sync, "resolve_source", side_effect=AssertionError("inventory scanned logs")):
            code, shown = self.run_management("show", SID[:8])
            self.assertEqual(shown["subscription"]["turn_count"], 1)
            code, listed = self.run_management("list", "--harness", "codex")
            self.assertEqual(len(listed["subscriptions"]), 1)
        self.assertEqual(before, {p: p.stat().st_mtime_ns for p in self.output.rglob("*") if p.is_file()})

    def test_unsubscribe_retains_documents_and_reenables(self):
        self.write_codex([message("user", "keep")])
        self.run_management("subscribe", SID)
        folder = self.output / SID
        (folder / "map.md").write_text("edited map")
        before = (folder / "prompts.md").read_bytes()
        code, result = self.run_management("unsubscribe", SID[:8])
        self.assertEqual(code, 0)
        self.assertFalse(result["subscription"]["subscribed"])
        self.run_management("unsubscribe", SID)
        self.assertTrue(sync.sync_all())
        self.assertFalse(sync.sync_source(sync.resolve_source(SID)))
        self.assertEqual((folder / "prompts.md").read_bytes(), before)
        self.assertEqual(self.run_management("list")[1]["subscriptions"], [])
        self.assertEqual(len(self.run_management("list", "--all")[1]["subscriptions"]), 1)
        self.run_management("subscribe", SID)
        self.assertTrue(sync.subscribed(folder))
        self.assertEqual((folder / "map.md").read_text(), "edited map")

    def test_sync_status_pending_error_and_missing(self):
        path = self.write_codex([message("user", "ready")])
        sync.sync(SID)
        folder = self.output / SID
        with path.open("ab") as stream:
            stream.write(b'{"unfinished":')
        self.assertEqual(sync.subscription_info(folder)["sync_status"], "pending")
        sync.sync_source(sync.resolve_source(SID))
        self.assertEqual(sync.subscription_info(folder)["sync_status"], "pending")
        sync.record_sync_error(folder, ValueError("bad source"))
        self.assertEqual(sync.subscription_info(folder)["sync_status"], "error")
        path.unlink()
        self.assertEqual(sync.subscription_info(folder)["sync_status"], "source_missing")

    def test_current_session_and_watcher_status(self):
        self.write_codex([message("user", "current")])
        with patch.dict(os.environ, {"CODEX_THREAD_ID": SID}, clear=True):
            code, result = self.run_management("subscribe", "--current", "--harness", "codex")
        self.assertEqual(code, 0)
        self.assertEqual(result["subscription"]["id"], SID)
        heartbeat = {"pid": os.getpid(), "updated_at": sync.datetime.now(sync.TZ).isoformat(),
                     "interval_seconds": 1, "output_root": str(self.output)}
        (self.output / ".watcher.json").write_text(json.dumps(heartbeat))
        self.assertEqual(sync.watcher_status()["status"], "running")
        self.assertTrue(sync.subscription_info(self.output / SID)["watching"])
        heartbeat["updated_at"] = "2000-01-01T00:00:00+08:00"
        (self.output / ".watcher.json").write_text(json.dumps(heartbeat))
        self.assertEqual(sync.watcher_status()["status"], "stale")

    def test_invalid_subscription_does_not_break_list(self):
        self.write_codex([message("user", "valid")])
        sync.sync(SID)
        broken = self.output / (SID[:-1] + "6")
        broken.mkdir()
        (broken / ".source.json").write_text("broken json")
        code, result = self.run_management("list")
        self.assertEqual(code, 0)
        self.assertEqual(len(result["subscriptions"]), 2)
        self.assertEqual(result["subscriptions"][1]["sync_status"], "error")
        code, result = self.run_management("show", "99999999")
        self.assertEqual(code, 1)
        self.assertIn("error", result)

    def test_source_attribution_without_daemon_session_environment(self):
        path = self.write_codex([record("turn_context", model="source-model")])
        with patch.dict(os.environ, {}, clear=True):
            header = SOURCE_ATTRIBUTION(sync.Source(SID, "codex", path))
        self.assertIn("agent name: source-model", header)
        self.assertIn("harness: codex", header)
        self.assertIn(f"session: {SID[:8]}", header)

    def test_attribution_ignores_caller_model_and_uses_archived_source(self):
        path = self.write_codex([record("turn_context", model="first-model"),
                                 record("turn_context", model="latest-model")])
        archived = self.root / "exported.jsonl"
        path.rename(archived)
        with patch.dict(os.environ, {"AI_MODEL_NAME": "wrong-model", "CODEX_THREAD_ID": "other"}):
            header = SOURCE_ATTRIBUTION(sync.Source(SID, "codex", archived))
        self.assertIn("agent name: latest-model", header)
        self.assertNotIn("wrong-model", header)

    def test_unknown_model_keeps_verified_source_identity(self):
        path = self.write_codex([message("user", "no model evidence")])
        header = SOURCE_ATTRIBUTION(sync.Source(SID, "codex", path))
        self.assertIn("agent name: unknown", header)
        self.assertIn("harness: codex", header)
        self.assertIn(f"session: {SID[:8]}", header)

    def test_antigravity_attribution_uses_source_brain(self):
        path = self.brain / SID / ".system_generated/logs/transcript_full.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"type": "USER_INPUT", "content":
                                    "setting `Model Selection` to Gemini 3.8 Flash (Medium)."}) + "\n")
        with patch.dict(os.environ, {"AI_MODEL_NAME": "wrong-model", "CODEX_THREAD_ID": "other"}):
            header = SOURCE_ATTRIBUTION(sync.Source(SID, "antigravity", path))
        self.assertIn("agent name: gemini-3.8-flash", header)
        self.assertIn("harness: antigravity", header)
        self.assertIn(f"conversation://{SID}", header)


if __name__ == "__main__":
    unittest.main()
