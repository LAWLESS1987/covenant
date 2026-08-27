@echo off
REM ===========================================================================
REM  ONE_PROBE.bat -- run probe_win_connect.py on Windows. 2026-08-27.
REM  Read-only: it opens sockets to ports where nothing is listening, times
REM  them, and READS the TCP settings. Nothing is bound, sent, or changed, and
REM  no node is touched. Output also goes to PROBE_WIN_CONNECT.txt.
REM  M28: logic in Python, GOTO labels, no parenthesised IF blocks.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title COVENANT -- WIN CONNECT PROBE
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe
echo.
"%PY%" probe_win_connect.py > PROBE_WIN_CONNECT.txt 2>&1
type PROBE_WIN_CONNECT.txt
echo.
echo   Saved to PROBE_WIN_CONNECT.txt
echo.
pause
endlocal
