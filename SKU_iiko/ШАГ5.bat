@echo off
title Step 5 - Deep probe
py "%~dp0step5_deep.py"
if errorlevel 1 python "%~dp0step5_deep.py"
pause
