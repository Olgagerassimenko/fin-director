@echo off
title Step 1 - Auth
py "%~dp0step1_auth.py"
if errorlevel 1 python "%~dp0step1_auth.py"
pause
