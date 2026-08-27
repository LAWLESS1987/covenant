@echo off
REM ============================================================
REM  Covenant PRODUCTION launch (real ethics gate)
REM  Needs a billed Anthropic API key. The gate calls the API to
REM  judge each transaction; without a working key it rejects all.
REM  Run in a terminal:  start_live.bat
REM ============================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

REM PRODUCTION env: real semantic judge, mock OFF. Child windows inherit these.
set "COVENANT_INSECURE_MOCK_JUDGE="
set COVENANT_JUDGE_PROVIDERS=claude

echo.
echo === Covenant PRODUCTION launch ===
echo The ethics gate will make real Anthropic API calls (a few hundredths of a
echo cent per transaction). You need an API key with billing set up.
echo   Get one: console.anthropic.com  (Billing first, then API Keys - Create Key)
echo.
set "ANTHROPIC_API_KEY="
set /p ANTHROPIC_API_KEY=Paste your Anthropic API key (sk-ant-...):
if "!ANTHROPIC_API_KEY!"=="" (
  echo.
  echo No key entered. Production cannot run without it - the gate rejects every
  echo transaction. Get a billed key, then run this again.
  pause & exit /b 1
)

if not exist "genesis.json" ( echo genesis.json missing - run run_setup.bat first. & pause & exit /b 1 )
if not exist "covenant_A.db.key" ( echo covenant_A.db.key missing - run run_setup.bat first. & pause & exit /b 1 )

echo.
echo Running readiness check -^> preflight_live.txt
python preflight.py --genesis genesis.json --db covenant_A.db > preflight_live.txt 2>&1
type preflight_live.txt | findstr /C:"checks:" /C:"READY" /C:"BLOCKING" /C:"judge configuration"

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

echo.
echo ============================================================
type live_out.txt
echo ============================================================
echo.
echo Saved to live_out.txt. If the send was REJECTED, the key/billing is the issue.
echo Tell Claude "done" and it will read live_out.txt.
pause
endlocal
