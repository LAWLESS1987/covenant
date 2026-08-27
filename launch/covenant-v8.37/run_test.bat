@echo off
REM ============================================================
REM  Comprehensive test against REAL live market data.
REM  Writes covenant_test_report.txt for Claude to read.
REM  Run in a terminal:  run_test.bat
REM ============================================================
setlocal
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

echo.
echo Running the full battery against live market data...
echo (fetching 16 symbols, ~800 strategy variants, this takes a few minutes)
echo.

python full_test.py --granularity hour

echo.
echo ============================================================
echo Report written to covenant_test_report.txt
echo Tell Claude "done" and it will read the results.
echo ============================================================
pause
endlocal
