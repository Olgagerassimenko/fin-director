@echo off
cd /d "C:\Users\Admin\Desktop\Claude\ФД"
del /f /q ".git\index.lock" 2>nul
git add -A
git diff --cached --quiet && exit /b 0
git commit -m "auto update"
git push
