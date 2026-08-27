@echo off
REM ===========================================================================
REM  ONE.bat -- the one double-click. 2026-08-27.
REM
REM  It replaces the reason you needed to remember which of AA..AP to run.
REM  All logic is in covenant_one.py, deliberately, and that same file is the
REM  one command in the cloud too -- so a cloud run and a PC run are the same
REM  task list executed by the same bytes, and a difference between them is a
REM  real difference in the machine, not in the runner.
REM
REM    ONE.bat                identity, coverage, gates, sweep, live state.
REM                           Touches nothing. ~45-75 min.
REM    ONE.bat --quick        everything except the long sweep. ~2 min.
REM    ONE.bat --check        gates only. Touches nothing at all.
REM    ONE.bat --restart      ...and then verify + restart the nodes.
REM    ONE.bat --dashboard    ...and then write and open dashboard.html
REM    ONE.bat --daily        ...and then the daily check + circuit breakers.
REM    ONE.bat --console      ...and then serve the console on 127.0.0.1:5199
REM    ONE.bat --all          sweep + dashboard + daily
REM
REM  Everything it prints also lands in ONE_RUN.txt, in full, including the
REM  tail of every suite that did not come out clean.
REM
REM  M28 throughout: all logic in Python, GOTO labels instead of parenthesised
REM  IF blocks, no bare "(" outside a REM, CRLF line endings. An unescaped ")"
REM  inside an IF block has silently aborted a script in this folder before,
REM  after three lines, with no error anywhere.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title COVENANT -- ONE
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

echo.
echo   ==========================================================
echo    COVENANT  --  ONE COMMAND
echo    Nothing hidden. Nothing silent. Nothing touched unless
echo    you passed a flag that says to touch it.
echo   ==========================================================
echo.

"%PY%" covenant_one.py %*
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" goto OK
if "%RC%"=="2" goto INCOMPLETE
goto FAILED

:OK
echo   PASS -- everything this runner names was measured and correct.
goto DONE

:INCOMPLETE
echo   INCOMPLETE -- nothing failed, something was not measured.
echo   Read the VERDICT block above. This is NOT a pass.
goto DONE

:FAILED
echo   FAIL -- something is wrong and it is named in the VERDICT block.
echo   The full transcript is in ONE_RUN.txt
goto DONE

:DONE
echo.
pause
endlocal
