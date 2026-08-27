@echo off
REM ===========================================================================
REM  ONE_UP.bat -- bring the nodes up. 2026-08-27.
REM
REM  ORDER MATTERS AND IT IS THE WHOLE POINT, same as AN_LAUNCH.bat:
REM
REM    1. identity, folder integrity and every launch gate, measured, changing
REM       NOTHING;
REM    2. only if no gate is BLOCKED does covenant_one.py hand over to
REM       verify_deploy.py, which hashes the delivery, refuses to restart over
REM       a judge that is not there, runs AB_RESTART_NODES.bat, and then asks
REM       each node what it is ACTUALLY running and compares that with disk.
REM
REM  If a gate is BLOCKED the restart is REFUSED BEFORE the stop, not after it
REM  (P17: a stop that always succeeds composed with a start that can refuse is
REM  not a restart, it is a stop).
REM
REM  Unlike AN_LAUNCH.bat this never asks a question, so it can be run by a
REM  double-click, a scheduler, or a remote session with no keyboard. The
REM  trade is deliberate and stated: AN_LAUNCH asks before proceeding through
REM  UNKNOWN gates, this one proceeds and NAMES every UNKNOWN in the transcript.
REM  Use AN_LAUNCH.bat when you are sitting in front of it.
REM
REM  The sweep is skipped here on purpose -- this is a launch, not a
REM  verification. Run ONE.bat for that.
REM
REM  Transcript: ONE_UP.txt, plus DEPLOY_VERIFY.txt and NODE_RESTART.txt.
REM  M28 throughout: logic in Python, GOTO labels, no parenthesised IF blocks.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title COVENANT -- ONE UP
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

echo.
echo   ==========================================================
echo    COVENANT  --  BRING THE NODES UP
echo    Gates first. The restart is refused if any gate BLOCKS.
echo   ==========================================================
echo.

"%PY%" covenant_one.py --quick --restart --out ONE_UP.txt
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" goto OK
if "%RC%"=="2" goto INCOMPLETE
goto FAILED

:OK
echo   PASS -- gates clear, nodes restarted, disk and running process agree.
goto DONE

:INCOMPLETE
echo   INCOMPLETE -- nothing failed, something could not be measured.
echo   Read the VERDICT block and DEPLOY_VERIFY.txt. This is NOT a pass.
goto DONE

:FAILED
echo   FAIL -- read the VERDICT block above and DEPLOY_VERIFY.txt.
echo   If the restart says REFUSED, a gate blocked it and nothing was stopped.
goto DONE

:DONE
echo.
pause
endlocal
