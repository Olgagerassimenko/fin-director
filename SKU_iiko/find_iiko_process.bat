@echo off
set "OUT=%~dp0processes_list.txt"
powershell -NoProfile -Command "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object Id, ProcessName, MainWindowTitle | Format-Table -AutoSize | Out-File -FilePath '%OUT%' -Encoding utf8"
echo Done: %OUT%
pause
