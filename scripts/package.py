#!/usr/bin/env python3
"""Build a source release without private databases or local research artifacts."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.2.0'
INCLUDE = ['server.py', 'lpl_schedule.py', 'public', 'tests', 'docs', 'scripts', '.github',
           '.gitignore', '.gitattributes', 'README.md', 'LICENSE', 'CONTRIBUTING.md',
           'CHANGELOG.md', '使用说明.md', '启动观赛搭子.command', '启动-Windows.bat']


def package():
    destination = ROOT / 'dist' / ('lol-worlds-watch-buddy-v%s.zip' % VERSION)
    destination.parent.mkdir(exist_ok=True)
    files = []
    for name in INCLUDE:
        path = ROOT / name
        if not path.exists():
            raise RuntimeError('发布文件缺失：%s' % name)
        paths = path.rglob('*') if path.is_dir() else [path]
        files.extend(p for p in paths if p.is_file() and '__pycache__' not in p.parts and p.name != '.DS_Store')
    with zipfile.ZipFile(str(destination), 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(str(path), str(Path('lol-worlds-watch-buddy') / path.relative_to(ROOT)))
    with zipfile.ZipFile(str(destination)) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('发布包完整性校验失败。')
        for name in archive.namelist():
            if '/data/' in name or '/work/' in name or '.sqlite' in name or '/.git/' in name:
                raise RuntimeError('发布包意外包含本地数据。')
    print('发布包：%s' % destination)
    print('%s 个文件，%s 字节；不包含本机数据库或测试房间。' % (len(files), destination.stat().st_size))
    return destination


if __name__ == '__main__':
    package()
