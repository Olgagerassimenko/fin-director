@echo off
title Проверка складов iiko
py "%~dp0check_departments.py"
if errorlevel 1 python "%~dp0check_departments.py"
pause
