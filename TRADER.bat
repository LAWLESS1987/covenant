@echo off
REM ===========================================================================
REM  TRADER.bat -- the local trading program. 2026-08-28.
REM
REM    TRADER.bat                status: nodes, venues, limits, counters
REM    TRADER.bat --once         one full cycle
REM    TRADER.bat --plan-only    plan and print; touch no venue at all
REM    TRADER.bat --loop         keep cycling until stopped
REM
REM  DISARMED BY DEFAULT. With armed=false in trader_config.json every order
REM  goes to the venue's VALIDATE endpoint -- Kraken validate=true, Coinbase
REM  /orders/preview -- so the real venue checks the real order against your
REM  real balance and books nothing.
REM
REM  TO STOP IT AT ANY TIME: create a file named TRADER_HALT in this folder.
REM  Ordering halts on the next cycle even while armed.
REM
REM  M28: no bare "(" outside a REM, CRLF line endings.
REM ===========================================================================
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
python covenant_trader.py %*
echo.
pause
