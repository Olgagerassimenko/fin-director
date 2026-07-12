@echo off
cd /d "%~dp0"
echo Обновляем сайт...
npx wrangler deploy
echo.
echo Готово! Сайт обновлён.
pause
