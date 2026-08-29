@echo off
REM ===========================================================================
REM  TRADE.bat -- the one double-click for the trading side. 2026-08-28.
REM
REM    TRADE.bat                read both exchanges, sync holdings, rule check
REM    TRADE.bat --no-sync      show the holdings diff, apply nothing
REM    TRADE.bat --check-only   skip the exchanges; check the file as it stands
REM
REM  All logic is in trade_daily.py, deliberately -- same reasoning as ONE.bat.
REM  A .bat that makes decisions is a .bat nobody can test.
REM
REM  It holds no key and places no order. The two balance readers it calls each
REM  hold their own READ-ONLY credential, outside this folder. See
REM  EXCHANGE_SETUP.md. Every order is yours, by hand, at the exchange.
REM
REM  M28: no bare "(" outside a REM, CRLF line endings.
REM ===========================================================================
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
python trade_daily.py %*
echo.
pause
