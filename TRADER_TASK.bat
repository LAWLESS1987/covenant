@echo off
REM ===========================================================================
REM  TRADER_TASK.bat -- the entry point the Windows scheduled task calls.
REM  2026-08-28.
REM
REM  Same program as TRADER.bat, with two differences that matter unattended:
REM    * no "pause" -- a scheduled run has nobody to press a key, and a paused
REM      task hangs forever holding its slot.
REM    * every run is appended to trader_log.txt, because an unattended run
REM      that prints to a window nobody sees has not reported anything.
REM
REM  It runs --once. Not --loop: the strategy reads DAILY closes and a 200-day
REM  line, so a second run in the same day sees the same settled bar and can
REM  only add API calls and duplicate orders, never signal.
REM
REM  WHEN IT DOES NOT RUN (measured 2026-09-02, settings changed 2026-09-06).
REM  As of 2026-09-06 the task has "run as soon as possible after a missed
REM  start" ON and the two battery conditions OFF, so a 09:00 that falls inside
REM  sleep runs on resume instead of being refused (the 0x800710E0 case).
REM  "Wake the computer" is still OFF: a PC that stays asleep all day still
REM  produces no run, and trader_freshness.py reads THIS log and exits 1 on
REM  such a day, which is the only place that day is visible.
REM
REM  Remove the task with:  schtasks /Delete /TN "CovenantTrader" /F
REM ===========================================================================
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
echo. >> trader_log.txt
echo ==== %DATE% %TIME% ==== >> trader_log.txt
python covenant_trader.py --once >> trader_log.txt 2>&1
