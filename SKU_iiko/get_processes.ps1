# Сохраняем список всех процессов с окнами в файл
$out = Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object Id, ProcessName, MainWindowTitle | Format-Table -AutoSize | Out-String
$out | Out-File "$PSScriptRoot\processes_list.txt" -Encoding utf8
Write-Host "Готово! Открываю файл..."
notepad "$PSScriptRoot\processes_list.txt"
