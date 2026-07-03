@echo off
cd /d "C:\Users\Admin\Desktop\Claude\ФД"
del /f /q ".git\index.lock" 2>nul
git add -A
git commit -m "add xlsx files and scripts"
git push
echo.
echo ГОТОВО! Все файлы отправлены на GitHub.
pause
