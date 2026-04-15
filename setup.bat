@echo off
title Sachalayatan Downloader — First Time Setup
cd /d "%~dp0"

echo.
echo  ========================================
echo   Sachalayatan Downloader — Setup
echo  ========================================
echo.

:: ── Check Python ──────────────────────────────────────────────────────────────
echo  Checking Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Python is not installed or not on PATH.
    echo.
    echo  Please do the following:
    echo    1. Go to https://www.python.org/downloads/
    echo    2. Click the big Download Python button
    echo    3. Run the installer
    echo    4. On the FIRST screen, tick "Add Python to PATH"
    echo    5. Re-run this setup file
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYVER=%%i
echo  Found: %PYVER%
echo.

:: ── Install packages ──────────────────────────────────────────────────────────
echo  Installing required packages...
echo  (this may take a minute)
echo.
python -m pip install --upgrade pip --quiet
python -m pip install requests beautifulsoup4 lxml flask --quiet

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Package installation failed.
    echo  Try running this command manually:
    echo.
    echo      pip install requests beautifulsoup4 lxml flask
    echo.
    pause
    exit /b 1
)

echo.
echo  ========================================
echo   Setup complete!
echo  ========================================
echo.
echo  To start the app, double-click start.bat
echo.
pause
