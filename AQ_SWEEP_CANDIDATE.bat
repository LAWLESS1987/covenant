@echo off
REM ===========================================================================
REM  AQ_SWEEP_CANDIDATE.bat -- sweep the CANDIDATE, not the deployed core.
REM  2026-08-29.
REM
REM  WHY THIS FILE EXISTS. run_local_sweep.py stages the DEPLOYED core, so the
REM  only way to sweep a change was to deploy it first -- the gate could only
REM  run after the thing it was meant to gate. v8.38 sat in pending-v8.38 for
REM  three days unswept for exactly that reason.
REM
REM  --candidate overlays pending-v8.38 onto the scratch tree in %TEMP% AFTER
REM  the deployed files. The suites then run against the candidate and the
REM  production folder is never written to. Nothing here can land anything.
REM
REM  It takes 10-15 minutes and it spawns real node processes in %TEMP%. The
REM  running nodes in THIS folder are untouched: the sweep matches leftovers on
REM  the scratch path in their command line, never on the port.
REM
REM  Results: SWEEP_CANDIDATE.txt in this folder, written and flushed AS EACH
REM  SUITE FINISHES, so you can watch it rather than wait for the end.
REM
REM  M28 throughout: GOTO labels, no parenthesised IF blocks, no bare "("
REM  outside a REM, CRLF endings.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title COVENANT SWEEP -- CANDIDATE
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe
set CAND=pending-v8.38
if not "%~1"=="" set CAND=%~1

if not exist "%CAND%\covenant_unified_v8.py" goto NOCAND

echo.
echo   ==========================================================
echo    COVENANT SWEEP  --  CANDIDATE: %CAND%
echo   ==========================================================
echo.
echo    The deployed covenant_unified_v8.py in this folder is NOT
echo    changed. The candidate is overlaid onto a scratch copy in
echo    %%TEMP%%\covenant_sweep and the suites run against that.
echo.
echo    10 to 15 minutes. Results append to SWEEP_CANDIDATE.txt as
echo    each suite finishes -- open it in another window to watch.
echo.

"%PY%" run_local_sweep.py --candidate "%CAND%" --out SWEEP_CANDIDATE.txt
set RC=%ERRORLEVEL%
echo.
if not "%RC%"=="0" goto FAILED
echo    Sweep finished. The verdict is the last few lines of
echo    SWEEP_CANDIDATE.txt -- look for GREEN or RED.
goto SHOW

:FAILED
echo    The sweep RUNNER exited %RC%. That is the runner failing, not
echo    the suites: read SWEEP_CANDIDATE.txt for how far it got.
goto SHOW

:SHOW
echo.
echo   ---------------- last lines ----------------
if exist SWEEP_CANDIDATE.txt powershell -NoProfile -Command "Get-Content SWEEP_CANDIDATE.txt -Tail 8"
goto END

:NOCAND
echo.
echo   No candidate found at "%CAND%\covenant_unified_v8.py".
echo   Pass a directory as the first argument, or put the candidate
echo   in pending-v8.38\.
goto END

:END
echo.
pause
