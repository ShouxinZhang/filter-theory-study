"""Session isolation and fail-closed regression tests (synthetic logs only)."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/get_model_name.py'
spec = importlib.util.spec_from_file_location('model_reader', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, path, events):
        f = self.root / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text('\n'.join(json.dumps(e) for e in events))
        return f

    def test_codex_auto_invalidates_previous_model(self):
        f = self.write('sessions/rollout-current.jsonl', [
            {'type': 'turn_context', 'payload': {'model': x}}
            for x in ['model-a', 'auto']])
        with f.open('a') as stream:
            stream.write('\n{"partial":')
        self.assertEqual(m.codex_model({'CODEX_HOME': str(self.root), 'CODEX_THREAD_ID': 'current'}), 'unknown')

    def test_codex_only_exact_session(self):
        self.write('sessions/rollout-othercurrent.jsonl', [{'type':'turn_context','payload':{'model':'wrong'}}])
        self.assertIsNone(m.codex_model({'CODEX_HOME':str(self.root),'CODEX_THREAD_ID':'current'}))
        self.assertIsNone(m.codex_model({'CODEX_HOME':str(self.root),'CODEX_THREAD_ID':'*'}))

    def test_copilot_no_latest_session_fallback(self):
        self.write('session-state/other/events.jsonl', [{'type':'session.start','data':{'model':'wrong'}}])
        self.assertIsNone(m.copilot_model({'COPILOT_HOME':str(self.root),'COPILOT_MODEL':'default-model'}))

    def test_copilot_resolved_model_and_auto_switch(self):
        env={'COPILOT_HOME':str(self.root),'COPILOT_SESSION_ID':'current'}
        events=[{'type':'session.start','data':{'model':'auto','resolvedModel':'resolved-model'}}]
        self.write('session-state/current/events.jsonl',events)
        self.assertEqual(m.copilot_model(env),'resolved-model')
        self.write('session-state/current/events.jsonl',events+[{'type':'session.model_change','data':{'newModel':'auto'}}])
        self.assertEqual(m.copilot_model(env),'unknown')

    def vscode_env(self, sid='sess-1'):
        log = self.root / 'ws/GitHub.copilot-chat/debug-logs' / sid
        log.mkdir(parents=True, exist_ok=True)
        return {'VSCODE_TARGET_SESSION_LOG': str(log)}

    def test_copilot_vscode_resolved_and_pending(self):
        env = self.vscode_env()
        sel = {'identifier': 'vendor/Group/prov/model-x',
               'metadata': {'id': 'prov/model-x'}}
        base = {'kind': 0, 'v': {'requests': [], 'inputState': {'selectedModel': sel}}}
        req = {'modelId': 'vendor/Group/prov/model-x'}
        f = 'ws/chatSessions/sess-1.jsonl'
        self.write(f, [base, {'kind': 2, 'k': ['requests'], 'v': [req]}])
        self.assertEqual(m.copilot_vscode_model(env), 'prov/model-x')
        self.write(f, [base, {'kind': 2, 'k': ['requests'], 'v': [req]},
                       {'kind': 1, 'k': ['requests', 0, 'result'],
                        'v': {'metadata': {'resolvedModel': 'real-model'}}}])
        self.assertEqual(m.copilot_vscode_model(env), 'real-model')

    def test_copilot_vscode_auto_and_isolation(self):
        env = self.vscode_env()
        self.write('ws/chatSessions/other.jsonl', [
            {'kind': 0, 'v': {'requests': [{'modelId': 'wrong'}]}}])
        self.assertIsNone(m.copilot_vscode_model(env))
        self.write('ws/chatSessions/sess-1.jsonl', [
            {'kind': 0, 'v': {'requests': [{'modelId': 'copilot/auto'}]}}])
        self.assertEqual(m.copilot_vscode_model(env), 'unknown')
        self.assertEqual(m.infer_framework({'AI_AGENT': 'github_copilot_vscode_agent'}),
                         'github-copilot-vscode')

    def test_claude_no_defaults_or_user_models(self):
        env={'CLAUDE_CONFIG_DIR':str(self.root),'ANTHROPIC_MODEL':'configured'}
        self.assertIsNone(m.claude_model(env))
        env['CLAUDE_SESSION_ID']='current'
        self.write('projects/project/current.jsonl',[
            {'type':'assistant','message':{'model':'actual-model'}},
            {'type':'user','message':{'model':'wrong'}}])
        self.assertEqual(m.claude_model(env),'actual-model')

    def test_opencode_requires_session(self):
        db=self.root/'session.db'
        with sqlite3.connect(db) as c:
            c.execute('CREATE TABLE session (id TEXT, model TEXT)')
            c.execute('INSERT INTO session VALUES (?, ?)',('current',json.dumps({'modelID':'model-a','providerID':'provider'})))
        env={'OPENCODE_DB':str(db),'OPENCODE_MODEL':'configured'}
        self.assertIsNone(m.opencode_model(env,self.root))
        env['OPENCODE_SESSION_ID']='current'
        self.assertEqual(m.opencode_model(env,self.root),'provider/model-a')

    def test_grok_bad_summary_and_missing_session(self):
        env={'GROK_HOME':str(self.root),'GROK_DEFAULT_MODEL':'configured'}
        self.assertIsNone(m.grok_model(env,self.root))
        env['GROK_SESSION_ID']='current'
        self.write('sessions/current/summary.json',[[]])
        self.assertIsNone(m.grok_model(env,self.root))

    def test_framework_does_not_match_substrings(self):
        with patch.object(m,'parent_commands',return_value='bash\nnot-codex\npython3'):
            self.assertIsNone(m.infer_framework({}))

    def test_explicit_auto_and_single_line(self):
        self.assertIsNone(m.clean_model('model\ninjected'))
        env=dict(os.environ,AI_MODEL_NAME='auto')
        result=subprocess.run(['python3',str(SCRIPT)],env=env,capture_output=True,text=True,check=True)
        self.assertEqual(result.stdout,'unknown\n')


if __name__ == '__main__':
    unittest.main()
