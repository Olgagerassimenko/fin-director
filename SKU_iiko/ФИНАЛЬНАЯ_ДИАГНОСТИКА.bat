@echo off
title Финальная диагностика iiko API
chcp 65001 > nul
echo Запускаю диагностику...
py "%~dp0diag_final.py"
if errorlevel 1 python "%~dp0diag_final.py"
pause
