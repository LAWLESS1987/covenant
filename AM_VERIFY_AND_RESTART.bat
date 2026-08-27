@echo off
REM ===========================================================================
REM  AM_VERIFY_AND_RESTART.bat  -- 2026-08-26, for the v8.37 propagation.
REM
REM  Closes the three-claims gap in one double-click (M38): the PROJECT, the
REM  file on DISK and the RUNNING process are three separate claims that drift
REM  independently, and this project has been caught by that repeatedly.
REM
REM  It verifies the copied files by sha256 FIRST and refuses to restart if
REM  they are not what was built and tested -- then restarts, then asks each
REM  node what it is actually running and compares that with the disk.
REM
REM  All logic is in verify_deploy.py, deliberately: cmd expands %% inside a
REM  python -c string and an earlier launcher printed nothing at all (M28).
REM  No parenthesised blocks anywhere below, for the same reason -- an
REM  unescaped ")" inside an IF block silently aborted a previous script.
REM
REM  Pass --no-restart to check the files and touch nothing.
REM ===========================================================================
setlocal
cd /d "%~dp0"
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

echo.
echo   Verifying the v8.37 delivery, restarting the nodes, and confirming
echo   the RUNNING processes report the source that is on disk.
echo   A copy of everything below is written to DEPLOY_VERIFY.txt
echo.

"%PY%" verify_deploy.py %*
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" goto ok
if "%RC%"=="2" goto incomplete
goto failed

:ok
echo   PASS - project, disk and running process all agree. Nothing to do.
goto done

:incomplete
echo   INCOMPLETE - nothing failed, but something could not be determined.
echo   Read DEPLOY_VERIFY.txt. This is NOT a pass.
goto done

:failed
echo   FAIL - read DEPLOY_VERIFY.txt before doing anything else. The nodes
echo   were NOT restarted if the file check was what failed.
goto done

:done
echo.
pause
endlocal
