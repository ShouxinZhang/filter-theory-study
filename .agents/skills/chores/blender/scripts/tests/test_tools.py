"""在隔离目录验证实验工具的授权边界、安装失败处理和任务退出状态。"""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
REPO = SCRIPTS.parents[4]


class ToolsTests(unittest.TestCase):
    def setUp(self):
        root = REPO / '.agents/.tmp/task/2026-11/2026-11-12_blender-skill/outputs/tests'
        root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def cli(self, name, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)],
                              capture_output=True, text=True, timeout=15)

    def archive(self, body=b'#!/bin/sh\necho "Blender 0.0.1"\n', name='package/blender', include_manifest=False):
        path = self.root / 'package.tar.xz'
        with tarfile.open(path, 'w:xz') as package:
            member = tarfile.TarInfo(name)
            member.mode = 0o755
            member.size = len(body)
            package.addfile(member, io.BytesIO(body))
            if include_manifest:
                existing = tarfile.TarInfo('package/installation.json')
                existing.size = 2
                package.addfile(existing, io.BytesIO(b'{}'))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return ['--archive', path, '--sha256', digest, '--version', '0.0.1',
                '--install-root', self.root / 'opt', '--user-confirmed']

    def test_consent_required_before_environment_execution(self):
        marker = self.root / 'executed'
        binary = self.root / 'fake-blender'
        binary.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\n')
        binary.chmod(0o755)
        result = self.cli('operations/inspect_env.py', '--blender', binary)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(marker.exists())

    def test_install_activate_profile_and_existing_destination(self):
        args = self.archive()
        source = self.root / 'old-profile'; source.mkdir()
        (source / 'userpref.blend').write_bytes(b'profile')
        target = self.root / 'new-profile'
        launcher = self.root / 'bin/blender'; launcher.parent.mkdir()
        launcher.symlink_to('/old/blender')
        args += ['--activate', '--launcher', launcher, '--profile-from', source, '--profile-to', target]
        result = self.cli('operations/install_release.py', *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((target / 'userpref.blend').read_bytes(), b'profile')
        self.assertEqual((source / 'userpref.blend').read_bytes(), b'profile')
        manifest = json.loads((self.root / 'opt/blender-0.0.1/installation.json').read_text())
        self.assertEqual(manifest['previous_launcher_target'], '/old/blender')
        self.assertEqual(launcher.resolve(), self.root / 'opt/blender-0.0.1/blender')
        again = self.cli('operations/install_release.py', *args)
        self.assertNotEqual(again.returncode, 0)
        self.assertEqual(launcher.resolve(), self.root / 'opt/blender-0.0.1/blender')

    def test_checksum_failure_leaves_install_root_absent(self):
        args = self.archive(); args[3] = '0' * 64
        result = self.cli('operations/install_release.py', *args)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'opt').exists())

    def test_unsafe_archive_cannot_escape_staging(self):
        result = self.cli('operations/install_release.py', *self.archive(name='../../escape'))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'escape').exists())
        self.assertFalse((self.root / 'opt/blender-0.0.1').exists())

    def test_wrong_version_preserves_existing_launcher(self):
        args = self.archive(body=b'#!/bin/sh\necho "Blender 9.9.9"\n')
        launcher = self.root / 'blender'; launcher.symlink_to('/old/blender')
        result = self.cli('operations/install_release.py', *args, '--activate', '--launcher', launcher)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(str(launcher.readlink()), '/old/blender')
        self.assertFalse((self.root / 'opt/blender-0.0.1').exists())

    def test_late_failure_restores_launcher_and_removes_only_new_paths(self):
        args = self.archive(include_manifest=True)
        launcher = self.root / 'blender'; launcher.symlink_to('/old/blender')
        source = self.root / 'old-profile'; source.mkdir()
        (source / 'setting').write_text('keep')
        target = self.root / 'new-profile'
        result = self.cli('operations/install_release.py', *args,
                          '--activate', '--launcher', launcher,
                          '--profile-from', source, '--profile-to', target)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(str(launcher.readlink()), '/old/blender')
        self.assertEqual((source / 'setting').read_text(), 'keep')
        self.assertFalse(target.exists())
        self.assertFalse((self.root / 'opt/blender-0.0.1').exists())

    def test_runner_failure_timeout_and_output_preservation(self):
        binary = self.root / 'fake-blender'
        script = self.root / 'job.py'; script.write_text('pass\n')
        binary.write_text('#!/bin/sh\necho failure\nexit 7\n'); binary.chmod(0o755)
        work = self.root / 'run'
        args = ['--blender', binary, '--script', script, '--work-dir', work, '--user-confirmed']
        result = self.cli('development/run.py', *args)
        self.assertEqual(result.returncode, 7, result.stderr)
        report = (work / 'run.json').read_bytes()
        self.assertEqual(json.loads(report)['exit_code'], 7)
        self.assertNotEqual(self.cli('development/run.py', *args).returncode, 0)
        self.assertEqual((work / 'run.json').read_bytes(), report)
        binary.write_text('#!/bin/sh\nsleep 5\n')
        args[5] = self.root / 'timeout'
        result = self.cli('development/run.py', *args, '--timeout', '.1')
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertTrue(json.loads((self.root / 'timeout/run.json').read_text())['timed_out'])


if __name__ == '__main__':
    unittest.main()
