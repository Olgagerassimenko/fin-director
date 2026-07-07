@echo off
chcp 65001 > nul
title Настройка автообновления iiko Dashboard

echo.
echo  Настройка автоматического обновления дашборда iiko
echo  ════════════════════════════════════════════════════
echo.
echo  Дашборд будет обновляться каждый день в 08:00
echo  (данные берутся напрямую из fudzavod.iiko.it)
echo.

SET SCRIPT_PATH=%~dp0generate.py
SET TASK_NAME=iiko_SKU_Dashboard

REM Удаляем старое задание если есть
schtasks /delete /tn "%TASK_NAME%" /f > nul 2>&1

REM Создаём новое задание — каждый день в 08:00
schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "python \"%SCRIPT_PATH%\" --auto" ^
  /sc DAILY ^
  /st 08:00 ^
  /ru "%USERNAME%" ^
  /f

IF %ERRORLEVEL% EQU 0 (
    echo  [OK] Задание создано: каждый день в 08:00
    echo.
    echo  Чтобы запустить сейчас вручную:
    echo    → ОБНОВИТЬ.bat
    echo.
    echo  Чтобы изменить время — запустите этот файл снова
    echo  и отредактируйте строку "/st 08:00"
) ELSE (
    echo  [ОШИБКА] Не удалось создать задание.
    echo  Попробуйте запустить от имени Администратора.
)

echo.
pause
