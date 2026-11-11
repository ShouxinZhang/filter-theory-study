"""新版地图路径、旧版迁移与人工内容保留的回归测试。"""
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from map_layout import ensure_map, map_path


class MapLayoutTests(unittest.TestCase):
    def setUp(self):
        repo = SCRIPTS.parents[4]
        root = repo / '.agents/.tmp/task/2026-11/2026-11-12_map-skill/outputs/test-data'
        root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def test_fresh_sync_creates_only_nested_map_and_preserves_empty_edit(self):
        target = ensure_map(self.directory, 'header', 'session-id')
        self.assertEqual(target, map_path(self.directory))
        self.assertIn('../prompts.md', target.read_text())
        self.assertFalse((self.directory / 'map.md').exists())
        target.write_text('')
        stamp = target.stat().st_mtime_ns
        ensure_map(self.directory, 'changed header', 'session-id')
        self.assertEqual(target.read_text(), '')
        self.assertEqual(target.stat().st_mtime_ns, stamp)

    def test_legacy_only_migrates_links_and_preserves_original_backup(self):
        original = ('[原文](prompts.md#p1) ![图片](assets/pic.png)\n'
                    '[网页](https://example.com) [锚点](#here)\n'
                    '[引用]: <assets/a b.png>\n'
                    '`[示例](prompts.md)`\n```md\n[x](prompts.md)\n```\n')
        legacy = self.directory / 'map.md'
        legacy.write_text(original)
        target = ensure_map(self.directory, 'header', 'session-id')
        result = target.read_text()
        self.assertIn('[原文](../prompts.md#p1)', result)
        self.assertIn('![图片](../assets/pic.png)', result)
        self.assertIn('[引用]: <../assets/a b.png>', result)
        self.assertIn('[网页](https://example.com) [锚点](#here)', result)
        self.assertIn('`[示例](prompts.md)`', result)
        self.assertIn('```md\n[x](prompts.md)\n```', result)
        self.assertFalse(legacy.exists())
        backups = list((self.directory / 'assets/legacy-map').glob('*.md'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), original)

    def test_both_versions_keep_current_and_archive_each_old_revision(self):
        target = ensure_map(self.directory, 'header', 'session-id')
        target.write_text('人类正在维护的地图')
        stamp = target.stat().st_mtime_ns
        legacy = self.directory / 'map.md'
        for text in ('old one', 'old two', 'old one'):
            legacy.write_text(text)
            ensure_map(self.directory, 'other header', 'session-id')
            self.assertFalse(legacy.exists())
        self.assertEqual(target.read_text(), '人类正在维护的地图')
        self.assertEqual(target.stat().st_mtime_ns, stamp)
        backups = list((self.directory / 'assets/legacy-map').glob('*.md'))
        self.assertEqual({p.read_text() for p in backups}, {'old one', 'old two'})
        ensure_map(self.directory, 'header', 'session-id')
        self.assertFalse(legacy.exists())


if __name__ == '__main__':
    unittest.main()
