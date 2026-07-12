@echo off
title Проверка май + Magnum в iiko
py "%~dp0diag_may_magnum.py"
if errorlevel 1 python "%~dp0diag_may_magnum.py"
pause
