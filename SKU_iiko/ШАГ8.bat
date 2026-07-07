@echo off
title Step 8 - Products API
py "%~dp0step8_products.py"
if errorlevel 1 python "%~dp0step8_products.py"
pause
