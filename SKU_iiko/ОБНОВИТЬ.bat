@echo off
title iiko SKU Dashboard

echo.
echo Подключение к iiko...
echo.

py "%~dp0generate.py"
if not errorlevel 1 goto ok

python "%~dp0generate.py"
if not errorlevel 1 goto ok

echo.
echo ОШИБКА: Python не найден.
echo Установите Python с https://python.org/downloads
pause
exit /b 1

:ok
echo.
echo Готово!
pause
