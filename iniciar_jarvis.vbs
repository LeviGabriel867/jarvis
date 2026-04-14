Set oFSO = CreateObject("Scripting.FileSystemObject")
Set oShell = CreateObject("WScript.Shell")

Dim pasta, script, cmd
pasta = oFSO.GetParentFolderName(WScript.ScriptFullName)
script = pasta & "\jarvis.py"

oShell.CurrentDirectory = pasta

cmd = "python " & Chr(34) & script & Chr(34)

' Mude para 1 se quiser ver a janela do console (util para debug)
oShell.Run cmd, 0, False
