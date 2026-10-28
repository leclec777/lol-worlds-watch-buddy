#!/usr/bin/env python3
"""Prepare release metadata from the checked-out app version and changelog."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import APP_VERSION
from scripts.package import VERSION


def release_metadata(changelog, app_version=APP_VERSION, package_version=VERSION):
    if app_version != package_version or not re.fullmatch(r'\d+\.\d+\.\d+', app_version):
        raise ValueError('应用版本与打包版本必须一致，且须使用 X.Y.Z 格式。')
    section = re.search(r'^## ' + re.escape(app_version) + r'(?=\s|$)[^\n]*\n(.*?)(?=^## |\Z)',
                        changelog, re.MULTILINE | re.DOTALL)
    if not section or not section.group(1).strip():
        raise ValueError('CHANGELOG 缺少当前版本的发布说明。')
    asset = 'lol-worlds-watch-buddy-v%s.zip' % app_version
    notes = section.group(1).strip() + '\n\n### 下载和启动\n\n'
    notes += '下载并解压 `%s`。需要 Python 3.8+，无需安装第三方依赖。\n\n' % asset
    notes += 'macOS 双击「启动观赛搭子.command」，Windows 双击「启动-Windows.bat」；'
    notes += '也可运行 `python3 server.py --open`。旧数据库和备份可继续使用。\n'
    return {'version': app_version, 'tag': 'v' + app_version, 'asset': asset, 'notes': notes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    info = release_metadata((ROOT / 'CHANGELOG.md').read_text(encoding='utf-8'))
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    notes = output / 'release-notes.md'
    notes.write_text(info.pop('notes'), encoding='utf-8')
    info.update(archive=str(ROOT / 'dist' / info['asset']), notes_file=str(notes))
    (output / 'release-metadata.json').write_text(json.dumps(info, ensure_ascii=False), encoding='utf-8')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as destination:
            for key, value in info.items():
                destination.write('%s=%s\n' % (key, value))
    print('Release prepared: %s (%s)' % (info['tag'], info['asset']))


if __name__ == '__main__':
    main()
