"""Exercise release contents and runtimes that report false success."""
import contextlib
import importlib.util
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


packager = load_script('package')
frontend = load_script('test_frontend')


class ToolingTests(unittest.TestCase):
    def test_source_release_contains_launchers_and_excludes_private_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'source'
            shutil.copytree(str(ROOT), str(root), ignore=shutil.ignore_patterns(
                '.git', 'data', 'dist', '__pycache__', 'work', 'outputs'))
            for name in ('data/nexus.sqlite3', 'work/private.json', 'dist/old.zip', '.env'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('private data')
            with mock.patch.object(packager, 'ROOT', root), contextlib.redirect_stdout(io.StringIO()):
                destination = packager.package()
            with zipfile.ZipFile(str(destination)) as archive:
                names = archive.namelist()
                for name in ('server.py', 'public/app.js', '启动观赛搭子.command',
                             '启动-Windows.bat', '.github/workflows/checks.yml', '.gitignore'):
                    self.assertIn('lol-worlds-watch-buddy/' + name, names)
                self.assertFalse(any('/data/' in name or '/work/' in name or '/dist/' in name
                                     or name.endswith('/.env') for name in names))
                self.assertIsNone(archive.testzip())

    def run_frontend(self, code=0, output='', error=None):
        result = subprocess.CompletedProcess([], code, stdout=output)
        with mock.patch.object(sys, 'argv', ['test_frontend.py', '--runtime', sys.executable]), \
                mock.patch.object(frontend.subprocess, 'run', return_value=result, side_effect=error), \
                contextlib.redirect_stdout(io.StringIO()):
            return frontend.main()

    def test_zero_exit_without_completed_suite_is_a_failure(self):
        self.assertEqual(self.run_frontend(output='PASS first test\nError: failed\n'), 1)

    def test_complete_suite_succeeds(self):
        self.assertEqual(self.run_frontend(output=frontend.SUCCESS_MARKER + '\n'), 0)

    def test_nonzero_exit_is_never_reported_as_success(self):
        self.assertEqual(self.run_frontend(code=1, output=frontend.SUCCESS_MARKER + '\n'), 1)

    def test_timed_out_suite_is_a_failure(self):
        self.assertEqual(self.run_frontend(error=subprocess.TimeoutExpired('runtime', 30)), 1)


if __name__ == '__main__':
    unittest.main()
