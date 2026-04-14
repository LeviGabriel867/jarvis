' JARVIS v3.0 - Windows Hidden Launcher
' Run the voice assistant without showing a console window
' Usage: Double-click this file, or call from command line

Set objShell = CreateObject("WScript.Shell")
strPath = objShell.CurrentDirectory

' Get the directory where this script is located
Set objFSO = CreateObject("Scripting.FileSystemObject")
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
strProjectRoot = objFSO.GetParentFolderName(strScriptDir)

' Run Python script silently
objShell.Run "python """ & strProjectRoot & "\scripts\run.py""", 0, False

' Alternative if above doesn't work:
' objShell.Run "cmd /c cd /d """ & strProjectRoot & """ && python scripts/run.py", 0, False
