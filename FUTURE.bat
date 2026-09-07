@echo off
REM ===========================================================================
REM  FUTURE.bat -- the one click. Asked 2026-09-06: "put a one click tab on my
REM  home screen that says future to begin".
REM
REM  What one click does, in order:
REM    1. If any covenant node is down, restart all three (AB_RESTART_NODES.bat);
REM       start the Sentinel-Witness seal service if it is not listening.
REM    2. ARM the trader: armed=true in trader_config.json. Your click is the
REM       arming; nothing arms it for you.
REM    3. Run one full cycle: read the venues, plan, seal the decision to the
REM       chain and mine it, then place an order ONLY if every gate clears --
REM       Rule 5 (30 settled signals that beat chance), the cash floor, the
REM       per-order and per-day caps, and the seal itself. While a gate holds,
REM       the order is VALIDATED against the venue and never booked, and the
REM       gate that held it is named on screen and in trader_log.txt.
REM
REM  To disarm: set "armed": false in trader_config.json, or create a file
REM  named TRADER_HALT next to this one.
REM ===========================================================================
setlocal
REM absolute, not %~dp0: a copy of this file on the Desktop must still run the repo.
cd /d "C:\Users\Lawre\covenant"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
echo.
echo  FUTURE -- covenant, one click     %DATE% %TIME%
echo  ---------------------------------------------------------------
set NODES_OK=1
curl -s -m 8 -o nul http://127.0.0.1:5000/health || set NODES_OK=0
curl -s -m 8 -o nul http://127.0.0.1:5020/health || set NODES_OK=0
curl -s -m 8 -o nul http://127.0.0.1:5060/health || set NODES_OK=0
if "%NODES_OK%"=="1" (
  echo  nodes: up
) else (
  echo  nodes: one or more down -- restarting all three
  call AB_RESTART_NODES.bat >nul 2>nul
  timeout /t 8 /nobreak >nul
)
call START_SEAL_SERVICE.bat
python -c "import json,time;p='trader_config.json';c=json.load(open(p));c['armed']=True;c['armed_by']='FUTURE.bat';c['armed_at']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());json.dump(c,open(p,'w'),indent=2);print('  armed: true  (your click, recorded in the config)')"
echo. >> trader_log.txt
echo ==== %DATE% %TIME%  FUTURE (one click) ==== >> trader_log.txt
python covenant_trader.py --once > "%TEMP%\future_run.txt" 2>&1
set RC=%ERRORLEVEL%
type "%TEMP%\future_run.txt"
type "%TEMP%\future_run.txt" >> trader_log.txt
echo.
if "%RC%"=="0" (
  echo  cycle finished. PLACED = real order. VALIDATED = a named gate held it back.
) else (
  echo  cycle exit %RC% -- read the lines above; 3 means the seal failed and nothing was placed.
)
echo  log: trader_log.txt      Rule 5 record: python signal_ledger.py
pause
