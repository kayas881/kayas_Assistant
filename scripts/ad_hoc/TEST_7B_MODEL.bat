@echo off
REM Quick test of your trained 7B model

echo.
echo ===================================
echo   Testing Kayas 7B Model
echo ===================================
echo.

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Run the quick test
python quick_test_7b.py

pause
