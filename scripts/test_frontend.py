#!/usr/bin/env python3
"""Run offline frontend tests; Python stdlib plus Node.js or macOS JavaScriptCore.

Usage (from the project folder):
    python3 scripts/test_frontend.py
    python3 scripts/test_frontend.py --runtime /absolute/path/to/node

No browser, network, package installation, or production dependency is used.
When neither JavaScript runtime is available the script exits with code 2 and
explains how to run the optional tests. The application itself only needs Python.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
JSC = Path('/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc')
SUCCESS_MARKER = 'NEXUS_FRONTEND_TESTS_OK'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', help='An existing Node.js or JavaScriptCore executable; nothing is installed.')
    args = parser.parse_args()
    runtime = args.runtime or shutil.which('node') or shutil.which('nodejs')
    if not runtime and JSC.is_file():
        runtime = str(JSC)
    if not runtime:
        print('Offline frontend tests require Node.js or the JavaScriptCore bundled with macOS.')
        print('If you already have Node.js, pass its path with --runtime. No production dependency is required.')
        return 2
    path = Path(runtime)
    if not path.is_file():
        print('JavaScript runtime does not exist: %s' % path)
        return 2
    # JavaScriptCore's CLI on older macOS builds mishandles non-ASCII path
    # arguments. Relative ASCII paths plus cwd work even in a Chinese folder.
    test_file = Path('tests') / 'frontend.test.js'
    app_file = Path('public') / 'app.js'
    is_jsc = path.name.lower() == 'jsc'
    command = [str(path), str(test_file)] + (['--'] if is_jsc else []) + [str(app_file)]
    print('Running offline frontend checks with %s' % path.name, flush=True)
    try:
        result = subprocess.run(command, cwd=str(ROOT), timeout=30, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
    except subprocess.TimeoutExpired:
        print('Offline frontend checks timed out after 30 seconds.')
        return 1
    print(result.stdout, end='')
    if result.returncode:
        return result.returncode
    # macOS JavaScriptCore can return zero even when quit(1) was requested.
    if SUCCESS_MARKER not in result.stdout.splitlines():
        print('Offline frontend checks did not complete successfully.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
