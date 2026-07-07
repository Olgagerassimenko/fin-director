@echo off
chcp 65001 > nul
title Автозапуск iiko Dashboard сервера

echo.
echo  Добавляю iiko Dashboard в автозапуск Windows...
echo.

REM Путь к bat-файлу запуска
SET SERVER_BAT=%~dp0ЗАПУСТИТЬ_СЕРВЕР.bat

REM Создаём ярлык в папке автозапуска
SET STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

REM Используем PowerShell для создания ярлыка
powershell -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%STARTUP_DIR%\iiko_SKU_Dashboard.lnk'); ^
   $s.TargetPath = 'python'; ^
   $s.Arguments = '\"%~dp0server.py\"'; ^
   $s.WorkingDirectory = '%~dp0'; ^
   $s.WindowStyle = 7; ^
   $s.Description = 'iiko SKU Dashboard Live Server'; ^
   $s.Save()"

IF %ERRORLEVEL% EQU 0 (
    echo  [OK] Сервер будет запускаться автоматически при входе в Windows
    echo.
    echo  Файл ярлыка: %STARTUP_DIR%\iiko_SKU_Dashboard.lnk
    echo.
    echo  Открываю дашборд в браузере...
    start "" "%SERVER_BAT%"
) ELSE (
    echo  [!] Не удалось создать ярлык автозапуска.
    echo      Запускайте ЗАПУСТИТЬ_СЕРВЕР.bat вручную.
)

echo.
pause
