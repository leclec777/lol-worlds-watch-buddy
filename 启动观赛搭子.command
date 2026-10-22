#!/bin/zsh
cd -- "${0:A:h}" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  print '请先安装 Python 3（https://www.python.org/downloads/），然后重新打开本文件。'
  read -r '?按回车键关闭。'
  exit 1
fi
python3 server.py --open
if [[ $? -ne 0 ]]; then
  read -r '?按回车键关闭。'
fi
