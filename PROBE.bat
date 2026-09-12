@echo off
REM ============================================================
REM  Finds which hosted AI judges actually work from THIS machine.
REM  (Until 2026-09-12 it probed a local model server first; that server
REM  was removed from this PC on 2026-09-07.)
REM ============================================================
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

echo.
echo Probing every judge endpoint with one real call each...
echo (hosted providers; a key must be set for each)
echo.

python judge_probe.py

echo.
echo ============================================================
echo  Copy everything above and paste it to Claude.
echo ============================================================
pause
endlocal
