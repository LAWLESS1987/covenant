@echo off
REM ============================================================
REM  Covenant PRODUCTION launch -- key from the ENVIRONMENT.
REM
REM  Identical to start_live.bat except for one thing: it never
REM  prompts for your API key, so the key is never echoed into the
REM  console window or left in its scrollback.
REM
REM  Set it once, in a normal (non-admin) terminal:
REM      setx ANTHROPIC_API_KEY "sk-ant-..."
REM  then CLOSE that terminal and open a new one (setx only
REM  affects processes started afterwards), and run this file.
REM
REM  To check it took:   echo %ANTHROPIC_API_KEY:~0,7%
REM  To remove it later: setx ANTHROPIC_API_KEY ""
REM ============================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

REM PRODUCTION env: real semantic judge, mock OFF. Child windows inherit these.
set "COVENANT_INSECURE_MOCK_JUDGE="
set COVENANT_JUDGE_PROVIDERS=claude

echo.
echo === Covenant PRODUCTION launch (key from environment) ===

if "%ANTHROPIC_API_KEY%"=="" (
  echo.
  echo ANTHROPIC_API_KEY is not set in this terminal.
  echo.
  echo   setx ANTHROPIC_API_KEY "sk-ant-..."
  echo.
  echo Then close this window, open a new terminal, and run this again.
  echo Without the key the ethics gate fails CLOSED: the nodes boot, peer,
  echo report healthy, and reject every single transaction.
  pause & exit /b 1
)
echo Key found in environment ^(starts %ANTHROPIC_API_KEY:~0,7%, not echoed in full^).
echo The gate makes a real Anthropic API call per transaction - a few
echo hundredths of a cent each. Billing must be set up on the key.
echo.

if not exist "genesis.json" ( echo genesis.json missing - run run_setup.bat first. & pause & exit /b 1 )
if not exist "covenant_A.db.key" ( echo covenant_A.db.key missing - run run_setup.bat first. & pause & exit /b 1 )

REM --- BACK UP THE FOUNDER KEY BEFORE ANYTHING ELSE -----------------
REM covenant_A.db.key is the founder identity AND the genesis mint key.
REM Losing it strands the genesis balance permanently.
if not exist "%USERPROFILE%\.covenant-keys" mkdir "%USERPROFILE%\.covenant-keys" >nul 2>nul
if not exist "%USERPROFILE%\.covenant-keys\covenant_A.db.key" (
  copy /y covenant_A.db.key "%USERPROFILE%\.covenant-keys\covenant_A.db.key" >nul
  echo Founder key backed up to %USERPROFILE%\.covenant-keys\
)

echo.
echo Running readiness check -^> preflight_live.txt
python preflight.py --genesis genesis.json --db covenant_A.db > preflight_live.txt 2>&1
type preflight_live.txt | findstr /C:"checks:" /C:"READY" /C:"BLOCKING" /C:"judge configuration"
echo.
echo NOTE: the "identity key permissions" FAIL is a POSIX-only check and can
echo       never clear on Windows. It is not a real blocker here.

REM fresh PRODUCTION databases; founder key -> node A so it holds the genesis 1000
for %%F in (nodeA_prod.db nodeA_prod.db-wal nodeA_prod.db-shm nodeB_prod.db nodeB_prod.db-wal nodeB_prod.db-shm) do if exist "%%F" del /q "%%F"
copy /y covenant_A.db.key nodeA_prod.db.key >nul

echo.
echo Starting node A (port 5000, LIVE)...
start "Covenant Node A (LIVE)" cmd /k "set COVENANT_DB_PATH=nodeA_prod.db&& python covenant_unified_v8.py --port 5000 --node-id A --genesis genesis.json --peers 127.0.0.1:5021"
echo Starting node B (port 5020, LIVE)...
start "Covenant Node B (LIVE)" cmd /k "set COVENANT_DB_PATH=nodeB_prod.db&& python covenant_unified_v8.py --port 5020 --node-id B --genesis genesis.json --peers 127.0.0.1:5001"

echo Waiting ~15s for nodes to come up and peer...
timeout /t 15 /nobreak >nul

echo == LIVE run through the real ethics gate == > live_out.txt
echo -- founder balance (expect 1000) -->> live_out.txt
python covenant_client.py balance --db nodeA_prod.db --of-key nodeA_prod.db.key >> live_out.txt 2>&1
echo -- send 10 A-^>B (the gate judges this) -->> live_out.txt
python covenant_client.py --port 5000 --key nodeA_prod.db.key send --to-key nodeB_prod.db.key --amount 10 >> live_out.txt 2>&1
echo -- mine -->> live_out.txt
python covenant_client.py --port 5000 --key nodeA_prod.db.key mine >> live_out.txt 2>&1
timeout /t 6 /nobreak >nul
echo -- status (expect converged True) -->> live_out.txt
python covenant_client.py status --ports 5000,5020 >> live_out.txt 2>&1
echo -- balances on BOTH dbs (they must agree) -->> live_out.txt
python covenant_client.py balance --db nodeA_prod.db --of-key nodeA_prod.db.key >> live_out.txt 2>&1
python covenant_client.py balance --db nodeB_prod.db --of-key nodeA_prod.db.key >> live_out.txt 2>&1
python covenant_client.py balance --db nodeA_prod.db --of-key nodeB_prod.db.key >> live_out.txt 2>&1
python covenant_client.py balance --db nodeB_prod.db --of-key nodeB_prod.db.key >> live_out.txt 2>&1

echo.
echo ============================================================
type live_out.txt
echo ============================================================
echo.
echo Expect: founder 1000 -^> 990, nodeB 10, converged True, and the
echo         founder/nodeB balances IDENTICAL across both dbs.
echo Saved to live_out.txt. Tell Claude "done" and it will read it.
pause
endlocal
