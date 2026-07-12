@echo off
cd /d "%~dp0"
del /f /q ".git\index.lock" 2>nul
git push origin main
echo.
echo Gotovo - Puls opublikovan na sajte.
pause
