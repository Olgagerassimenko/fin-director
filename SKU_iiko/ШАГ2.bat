@echo off
title Step 2 - Find Stores
py "%~dp0step2_stores.py"
if errorlevel 1 python "%~dp0step2_stores.py"
pause
