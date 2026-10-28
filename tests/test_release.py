"""Do not publish an archive whose version or release notes do not match."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare_release', ROOT / 'scripts' / 'prepare_release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_requested_version_extracts_only_its_changelog_section(self):
        info = release.release_metadata('## 1.2.0 — 2026-10-28\n新增赛后讨论。\n\n## 1.1.1\n旧版本说明。',
                                        '1.2.0', '1.2.0')
        self.assertEqual(info['tag'], 'v1.2.0')
        self.assertEqual(info['asset'], 'lol-worlds-watch-buddy-v1.2.0.zip')
        self.assertIn('赛后讨论', info['notes'])
        self.assertNotIn('## 1.1.1', info['notes'])

    def test_mismatched_archive_version_stops_release(self):
        with self.assertRaises(ValueError):
            release.release_metadata('## 1.2.0\nnotes', '1.2.0', '1.1.0')

    def test_missing_release_notes_stop_release(self):
        with self.assertRaises(ValueError):
            release.release_metadata('## 1.1.0\nold notes', '1.2.0', '1.2.0')

    def test_similar_version_heading_cannot_supply_the_notes(self):
        with self.assertRaises(ValueError):
            release.release_metadata('## 1.2.01\nwrong version', '1.2.0', '1.2.0')

    def test_invalid_version_cannot_become_a_tag(self):
        with self.assertRaises(ValueError):
            release.release_metadata('notes', '1.2.0\ninvalid', '1.2.0\ninvalid')


if __name__ == '__main__':
    unittest.main()
