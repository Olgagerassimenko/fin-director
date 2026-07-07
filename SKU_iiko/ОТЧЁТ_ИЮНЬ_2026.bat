@echo off
title iiko - Sales Report June 2026
echo.
echo  Generating June 2026 sales report from iiko...
echo.
py "%~dp0generate_june2026.py"
if errorlevel 1 python "%~dp0generate_june2026.py"
echo.
echo  Opening HTML report...
start "" "%~dp0..\продажи_июнь_2026_iiko.html"
pause
