@echo off
cd /d "C:\Users\Admin\Desktop\Claude\ФД"
del /f /q ".git\index.lock" 2>nul
git add продажи_2026.html index.html
git commit -m "add продажи_2026: май 265М, годовой график, Magnum 28М"
git push
echo.
echo ============================================
echo  ГОТОВО! продажи_2026.html загружен на GitHub
echo  Netlify обновится автоматически (если есть кредиты)
echo ============================================
pause
