@echo off
REM Создаём задачу в Планировщике Windows - автопуш каждые 30 минут
schtasks /create /tn "GitAutoPush_FD" /tr "\"C:\Users\Admin\Desktop\Claude\ФД\autopush.bat\"" /sc minute /mo 30 /ru "%USERNAME%" /f

if %errorlevel%==0 (
    echo.
    echo ГОТОВО! Сайт будет обновляться автоматически каждые 30 минут.
    echo.
) else (
    echo.
    echo Ошибка. Попробуйте запустить от имени администратора.
    echo.
)
pause
