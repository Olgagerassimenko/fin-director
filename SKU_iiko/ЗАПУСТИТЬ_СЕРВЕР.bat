@echo off
title iiko SKU Dashboard - Live Server

netstat -an | find "8080" | find "LISTEN" > nul 2>&1
if not errorlevel 1 (
    echo Server already running. Opening browser...
    start http://localhost:8080
    exit /b
)

echo.
echo  iiko SKU Dashboard - Live Server
echo  http://localhost:8080
echo  Do not close this window.
echo.

py "%~dp0server.py"
if errorlevel 1 (
    python "%~dp0server.py"
)

if errorlevel 1 (
    echo.
    echo  Error. Try: py -m pip install requests openpyxl
    pause
)
