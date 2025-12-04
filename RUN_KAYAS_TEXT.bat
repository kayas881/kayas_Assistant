@echo off
echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Starting Kayas in text mode...
python kayas_background.py

pause
