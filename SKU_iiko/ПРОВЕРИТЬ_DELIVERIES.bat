@echo off
title Проверка DELIVERIES
py "%~dp0diag_deliveries.py"
if errorlevel 1 python "%~dp0diag_deliveries.py"
pause
