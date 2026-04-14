Set oFSO = CreateObject("Scripting.FileSystemObject")
Set oShell = CreateObject("WScript.Shell")

Dim pasta, pythonExe, script, cmd
pasta = oFSO.GetParentFolderName(WScript.ScriptFullName)
pythonExe = "C:\Python312\python.exe"
script = pasta & "\jarvis.py"

' Muda o diretório de trabalho para a pasta do projeto
oShell.CurrentDirectory = pasta

' Monta o comando com aspas usando Chr(34) para evitar problemas com espaços no caminho
cmd = Chr(34) & pythonExe & Chr(34) & " " & Chr(34) & script & Chr(34)

' Mude para 1 se quiser ver a janela do console (útil para debug)
oShell.Run cmd, 0, False
