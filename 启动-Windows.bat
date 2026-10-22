@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo 请先安装 Python 3：https://www.python.org/downloads/
  pause
  exit /b 1
)
python server.py --open
if errorlevel 1 pause
