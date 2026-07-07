@echo off
title Check iiko report types
py "%~dp0check_report_types.py"
if errorlevel 1 python "%~dp0check_report_types.py"
pause
