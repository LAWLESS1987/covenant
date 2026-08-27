@echo off
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"
python daily.py --push covenant-lawre-7k3m9x
echo.
pause
