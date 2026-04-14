@echo off
REM JARVIS v3.0 - Windows Launcher (with console)
REM Run the voice assistant with console window visible

cd /d "%~dp0.."
python scripts/run.py %*
pause
