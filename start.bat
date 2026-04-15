@echo off
title Sachalayatan Downloader
cd /d "%~dp0"

echo.
echo  ========================================
echo   Sachalayatan Downloader
echo  ========================================
echo.
echo  Starting... your browser will open soon.
echo  Keep this window open while using the app.
echo  To stop: close this window.
echo.

python app.py

echo.
echo  The app has stopped.
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  Something went wrong. Make sure you have installed
    echo  the required packages by running:
    echo.
    echo      pip install requests beautifulsoup4 lxml flask
    echo.
)
pause
