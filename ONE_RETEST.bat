@echo off
REM ===========================================================================
REM  ONE_RETEST.bat -- re-run ONLY the suites that did not come out clean,
REM  ALONE and TWICE each. 2026-08-27.
REM
REM  WHY TWICE, AND WHY ALONE. M18/M20: a suite that fails while thirty-nine
REM  others share the CPU has not failed yet. It has failed when it fails on
REM  its own, twice. Both suites below start REAL processes and wait on a
REM  socket, which is exactly the shape that loses a race under load.
REM
REM  Edit the --only list when the failures change. Everything it prints also
REM  lands in ONE_RETEST.txt.
REM
REM  M28 throughout: logic in Python, GOTO labels, no parenthesised IF blocks.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title COVENANT -- ONE RETEST
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

echo.
echo   ==========================================================
echo    RETEST  --  the not-clean suites, alone, twice each
echo   ==========================================================
echo.

"%PY%" covenant_one.py --only test_a23_ack_health.py test_w2_sandbox_platform.py --repeat 2 --verbose --out ONE_RETEST.txt
set RC=%ERRORLEVEL%

echo.
echo   Full transcript: ONE_RETEST.txt
echo.
pause
endlocal
