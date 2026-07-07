@echo off
title Step 10 - Probe Fields
py "%~dp0step10_probe_fields.py"
if errorlevel 1 python "%~dp0step10_probe_fields.py"
pause
