@echo off
chcp 65001 >nul
echo ========================================
echo  Скачивание библиотек (один раз)
echo ========================================
echo.

cd /d "%~dp0"

echo Скачиваю Chart.js...
powershell -Command "Invoke-WebRequest -Uri 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js' -OutFile 'chart.min.js' -UseBasicParsing"

echo Скачиваю SheetJS (xlsx)...
powershell -Command "Invoke-WebRequest -Uri 'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js' -OutFile 'xlsx.min.js' -UseBasicParsing"

echo Скачиваю Chart Annotation plugin...
powershell -Command "Invoke-WebRequest -Uri 'https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js' -OutFile 'chartjs-annotation.min.js' -UseBasicParsing"

echo.
echo Проверяю...
if exist chart.min.js (echo [OK] chart.min.js) else (echo [!!] chart.min.js не скачан)
if exist xlsx.min.js (echo [OK] xlsx.min.js) else (echo [!!] xlsx.min.js не скачан)
if exist chartjs-annotation.min.js (echo [OK] chartjs-annotation.min.js) else (echo [!!] chartjs-annotation.min.js не скачан)

echo.
echo Теперь запустите ОБНОВИТЬ.bat для генерации дашборда.
pause
