@echo off
REM ===========================================================================
REM  AN_LAUNCH.bat -- the one double-click. 2026-08-26, for v8.37.
REM
REM  ORDER MATTERS AND IT IS THE WHOLE POINT:
REM
REM    1. launch_check.py   asks every gate and CHANGES NOTHING.
REM    2. only if nothing is BLOCKED does it hand over to verify_deploy.py,
REM       which hashes the delivery and then restarts.
REM
REM  So a bad copy, a dead judge or a paging model stops this BEFORE anything
REM  is stopped. P17: a stop that always succeeds composed with a start that
REM  can refuse is not a restart, it is a stop.
REM
REM  M28 is obeyed throughout: all logic in Python, GOTO labels instead of
REM  parenthesised IF blocks, and no bare "(" outside a REM. An unescaped ")"
REM  inside an IF block silently aborted an earlier script in this folder
REM  after three lines, with no error anywhere.
REM
REM    AN_LAUNCH.bat              check, then verify, then restart
REM    AN_LAUNCH.bat --check      check only. Touches nothing at all.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title COVENANT LAUNCH
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

echo.
echo   ==========================================================
echo    COVENANT LAUNCH  --  gates first, restart second
echo   ==========================================================
echo.

"%PY%" launch_check.py
set GC=%ERRORLEVEL%
"%PY%" launch_check.py --json > LAUNCH_CHECK.json 2>nul

echo.
if "%GC%"=="1" goto BLOCKED
if /i "%~1"=="--check" goto CHECKONLY
if "%GC%"=="2" goto ASK
goto RESTART

:BLOCKED
echo   ----------------------------------------------------------
echo    BLOCKED. Nothing was stopped and nothing was started.
echo    Read the BLOCKED lines above; each carries its own fix.
echo    A machine-readable copy is in LAUNCH_CHECK.json
echo   ----------------------------------------------------------
goto DONE

:CHECKONLY
echo   --check was passed. Stopping here by request. Nothing touched.
goto DONE

:ASK
echo   ----------------------------------------------------------
echo    Nothing is BLOCKED, but some gates could not be measured.
echo    That is NOT a pass. Read them above.
echo   ----------------------------------------------------------
echo.
choice /c YN /n /m "   Continue to verify and restart anyway? [Y/N] "
if errorlevel 2 goto ABORTED
goto RESTART

:ABORTED
echo   Stopped at your request. Nothing was touched.
goto DONE

:RESTART
echo.
echo   Gates clear. Handing over to verify_deploy.py -- it hashes the
echo   delivery, refuses to restart over a judge that is not there, then
echo   asks each node what it is ACTUALLY running.
echo.
"%PY%" verify_deploy.py
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" goto OK
if "%RC%"=="2" goto INCOMPLETE
goto FAILED

:OK
echo   PASS -- disk and running process agree. The launch is done.
echo   Next: python run_local_sweep.py   -- the win32 sweep, ~45 min
goto DONE

:INCOMPLETE
echo   INCOMPLETE -- nothing failed, something could not be determined.
echo   Read DEPLOY_VERIFY.txt. This is NOT a pass.
goto DONE

:FAILED
echo   FAIL -- read DEPLOY_VERIFY.txt before doing anything else.
goto DONE

:DONE
echo.
pause
endlocal
