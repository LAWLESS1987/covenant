@echo off
REM Re-run only the suites that did not fully pass in the sweep, ALONE and
REM twice each -- M18/M20: a failure while 23 other suites and two nodes share
REM the CPU is not a failure yet. Written 2026-08-22.
setlocal
cd /d "%~dp0"
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe
"%PY%" run_local_sweep.py --out RETEST_RESULTS.txt --repeat 2 test_a1a_a2.py test_a1_kill_matrix.py test_multinode_live.py
type RETEST_RESULTS.txt
echo.
pause
endlocal
