Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d ""C:\Users\crapisardi\Desktop\ProgrammiCodice\MaquetaWeb"" && python deploy_webhook.py", 0, False
Set WshShell = Nothing
