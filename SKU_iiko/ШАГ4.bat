@echo off
title Step 4 - Find Fields
py "%~dp0step4_fields.py"
if errorlevel 1 python "%~dp0step4_fields.py"
pause
