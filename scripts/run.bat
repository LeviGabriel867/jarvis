@echo off
REM JARVIS v3.0 - Windows Launcher (background, no console window)

cd /d "%~dp0.."
start "" /b pythonw scripts/run.py %*
