@echo off
title Step 3 - Report Types
py "%~dp0step3_report_types.py"
if errorlevel 1 python "%~dp0step3_report_types.py"
pause
