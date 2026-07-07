@echo off
title Step 9 - TRANSACTIONS
py "%~dp0step9_transactions.py"
if errorlevel 1 python "%~dp0step9_transactions.py"
pause
