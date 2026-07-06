@echo off
chcp 65001 >nul
echo ========================================
echo   SKU-дашборд — обновление данных
echo ========================================
echo.
echo Читаю Excel и генерирую дашборд...
echo.

python "%~dp0generate.py"
if %errorlevel% neq 0 (
    echo.
    echo ОШИБКА при генерации. Проверьте:
    echo  1. Установлен ли Python?
    echo  2. Установлен ли openpyxl?  pip install openpyxl
    echo  3. Есть ли Excel-файл в папке?
    pause
    exit /b 1
)

echo.
start "" "%~dp0дашборд.html"
echo Дашборд открыт в браузере.
timeout /t 2 >nul
