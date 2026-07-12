@echo off
title Дашборд продаж — Live iiko
echo.
echo  Запуск дашборда продаж...
echo  Открывайте: http://localhost:8090
echo.

py "%~dp0server_sales.py"
if not errorlevel 1 goto end

python "%~dp0server_sales.py"
if not errorlevel 1 goto end

echo.
echo  ОШИБКА: Python не найден.
echo  Установите Python с https://python.org/downloads
pause

:end
