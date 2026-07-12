@echo off
title Проверка TRANSACTIONS DateTime
py "%~dp0diag_transactions2.py"
if errorlevel 1 python "%~dp0diag_transactions2.py"
pause
