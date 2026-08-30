@echo off
REM ===========================================================================
REM  FIX_GUARD_BATTERY.bat -- one double-click. The click is the approval.
REM  2026-08-30.
REM
REM  The CovenantGuard task is gated OFF on battery, and it is the TOP of the
REM  supervision chain: it revives the watchdog, the watchdog revives the
REM  nodes, and nothing sits above it. Measured from logs/guard.log: 504
REM  minutes of gaps over five minutes across a 1459-minute window -- 35% of
REM  its logged life with nothing supervising the watchdog.
REM
REM  It resumes on mains power, so every check made while plugged in reports
REM  healthy. That is what let it run for weeks.
REM
REM  The script shows the current settings, shows exactly what it will change,
REM  waits for you to type YES, applies four fields IN PLACE, reads them back,
REM  and prints the reversal. It restarts nothing.
REM
REM  Logic lives in the .ps1, following this project's own convention -- cmd
REM  eats % and once turned a healthy record into "the record does not verify".
REM ===========================================================================
setlocal
cd /d "%~dp0"
title COVENANT -- GUARD ON BATTERY
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix_guard_battery.ps1"
echo.
pause
endlocal
