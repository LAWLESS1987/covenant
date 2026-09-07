@echo off
REM ===========================================================================
REM  START_SEAL_SERVICE.bat -- start the Sentinel-Witness seal service if it is
REM  not already listening on 127.0.0.1:8433. 2026-09-06 ("make sentinel local").
REM
REM  The service (sentinel_witness/seal_service.py) is what tradeGate.js seals
REM  through: it signs the proposed order as a zero-amount self-send, the local
REM  judges decide, the node keeps and mines it. It places no order and holds
REM  no exchange credential. Loopback only.
REM
REM  Renamed 2026-09-07 from SEAL_SERVICE_START.bat. In this repository a
REM  leading SEAL_ means a seal OUTPUT, and covenant_seal excludes such files
REM  from the set it seals so that producing a proof cannot change the set the
REM  proof is about. A launcher named SEAL_* broke that convention and
REM  test_m2_merkle_seal.py caught it (S3).
REM
REM  A copy of this file sits in the per-user Startup folder, so it runs at
REM  logon without administrator rights (a scheduled ONLOGON task needs them).
REM  FUTURE.bat calls it too. Safe to run twice: it checks the port first.
REM ===========================================================================
setlocal
cd /d "C:\Users\Lawre\covenant"
netstat -ano | findstr /R /C:":8433 .*LISTENING" >nul 2>nul
if %errorlevel%==0 (
  echo  seal service: already listening on 127.0.0.1:8433
  exit /b 0
)
set PYW=.venv\Scripts\pythonw.exe
if not exist "%PYW%" set PYW=pythonw.exe
start "" /B "%PYW%" "ops\hidden_task.py" sentinel_witness/seal_service.py
echo  seal service: started on 127.0.0.1:8433
exit /b 0
