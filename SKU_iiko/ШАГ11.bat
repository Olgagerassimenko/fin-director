@echo off
title Step 11 - Date Filter
py "%~dp0step11_date_filter.py"
if errorlevel 1 python "%~dp0step11_date_filter.py"
pause
