@echo off
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"
python daily.py --push auto
echo.
pause
