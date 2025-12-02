@echo off
REM Kayas Background Service Launcher
REM This script starts Kayas in the background with continuous listening

echo ========================================
echo Starting Kayas Background Service
echo ========================================
echo.

cd /d "%~dp0"

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Start the background service
python kayas_background.py

pause
