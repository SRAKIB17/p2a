@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo         P2A Academy Video Downloader Launcher
echo ============================================================
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" downloader.py %*
) else (
    python downloader.py %*
)
pause
