' Snow silent launcher (ASCII only - cscript reads ANSI)
Option Explicit
Dim sh, fso, root, pyw, main, q
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
main = root & "\main.py"
q = Chr(34)
pyw = ""
If fso.FileExists(root & "\.venv\Scripts\pythonw.exe") Then
  pyw = root & "\.venv\Scripts\pythonw.exe"
Else
  ' Fall back to pythonw.exe on PATH
  pyw = "pythonw.exe"
End If
sh.CurrentDirectory = root
On Error Resume Next
sh.Run q & pyw & q & " " & q & main & q, 0, False
If Err.Number <> 0 Then
  MsgBox "Python not found. Install Python 3.10+ or create .venv in the Snow folder.", 16, "Snow"
End If
