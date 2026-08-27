@echo off
REM ===========================================================================
REM  AA_INTEGRATE_AND_RUN.bat  (v3 -- 2026-08-22)
REM  Runs the verification sweep on THIS machine against the deployed
REM  covenant_unified_v8.py, in %TEMP%\covenant_sweep. The node restart lives
REM  in AB_RESTART_NODES.bat now -- one job per launcher.
REM  run_local_sweep.py appends each result to SWEEP_RESULTS.txt as it happens,
REM  and kills any leftovers from a previous sweep first (never the nodes).
REM  No parenthesised blocks: an unescaped ")" inside an IF block killed v1.
REM ===========================================================================
setlocal
cd /d "%~dp0"
set OUT=INTEGRATE_RESULTS2.txt
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

> "%OUT%" echo ==== local sweep  %DATE% %TIME% ====
>> "%OUT%" echo --- deployed core sha256 ---
certutil -hashfile covenant_unified_v8.py SHA256 | findstr /v /i "certutil hash" >> "%OUT%"
>> "%OUT%" echo --- python ---
"%PY%" -V >> "%OUT%" 2>&1
>> "%OUT%" echo.
"%PY%" run_local_sweep.py >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo ==== DONE %DATE% %TIME% ====
type SWEEP_RESULTS.txt
echo.
echo Finished. SWEEP_RESULTS.txt has the table; it was written line by line as it ran.
pause
endlocal
